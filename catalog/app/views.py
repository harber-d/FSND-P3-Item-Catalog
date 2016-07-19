import os
import random
import string
import json
from oauth2client import client
import oauth2client
import httplib2

from werkzeug.contrib.atom import AtomFeed
from sqlalchemy import desc
from apiclient.discovery import build

from app import app, models, db
from flask import render_template, request, session, make_response, url_for
from flask import redirect, Markup
from forms import ItemForm, CategoryForm


@app.route('/', methods=['GET'])
def get_items():
    """Returns all items in the catalog."""
    return render_template('items.html',
                           categories=models.Category.query.all(),
                           latest_items=models.Item.query.order_by(
                               desc(models.Item.created)).all())


@app.route('/login', methods=['GET'])
def login():
    """
    Redirects the user to google login if not signed in,
    otherwise redirects to main page.
    """
    if needs_login():
        return redirect(url_for('oauth2callback'))
    return redirect(url_for('get_items'))


@app.route('/oauth2callback')
def oauth2callback():
    """Callback method for Google Oauth2 flow."""

    # Following code adapted from Google API OAuth2 for Web Server Applications
    # guide: http://bit.ly/1XBFDVO
    print "starting flow"
    flow = client.flow_from_clientsecrets('client_secrets.json',
                                          scope='profile',
                                          redirect_uri=url_for('oauth2callback',
                                                               _external=True))
    print "returned from flow"
    if 'code' not in request.args:
        print "no code"
        auth_uri = flow.step1_get_authorize_url()
        return redirect(auth_uri)
    else:
        print "got code"
        auth_code = request.args.get('code')
        credentials = flow.step2_exchange(auth_code)
        print "got credentials"
        session['credentials'] = credentials.to_json()

    try:
        http = httplib2.Http()
        http = credentials.authorize(http)
        google_request = build('oauth2', 'v2').userinfo().get()
        result = google_request.execute(http=http)
        print json.dumps(result)

        # load the user from the DB or create a new one if new uesr
        user = models.User.query.filter_by(user_id=result['id']).first()
        if user is None:
            user = models.User(user_id=result['id'],
                               name=result['name'],
                               pic=result['picture'])
            db.session.add(user)
            db.session.commit()

        # store user details in the session
        session['user'] = user.user_id
        session['user_name'] = user.name
        session['user_pic'] = user.pic

        return redirect(url_for('get_items'))
    except client.AccessTokenRefreshError:
        return render_template('generic.html',
                               title="Access Token Refresh Error",
                               description="Oops. We couldn't refresh the " +
                                           "access token for some reason.",
                               redirect_to_index=False)


@app.route('/logout', methods=['GET'])
def logout():
    """Logs out from Google signin and redirects to index."""
    if 'credentials' in session:
        # attempt to obtain credentials and revoke access
        try:
            credentials = client.OAuth2Credentials.from_json(
                session['credentials'])
            if credentials is not None:
                credentials.revoke(httplib2.Http())
        except:
            pass
        finally:
            # remove credentials and user data from session in any case
            session.pop('credentials', None)
            session.pop('user', None)
            session.pop('user_name', None)
            session.pop('user_pic', None)
    return redirect(url_for('get_items'))


@app.route('/catalog/<category_name>/<item_name>', methods=['GET'])
def item_detail(category_name, item_name):
    """Returns catalog item detail page."""
    item = models.Item.query.filter(models.Category.name == category_name,
                                    models.Item.name == item_name).first()
    if item is not None:
        return render_template('item_detail.html',
                               item=item,
                               can_edit=is_same_user(item))
    return render_template('generic.html',
                           title="Item Not Found",
                           description="We couldn't find that item.",
                           redirect_to_index=False)


@app.route('/catalog/<category_name>/<item_name>/edit', methods=['GET'])
def edit_item(category_name, item_name):
    """Returns catalog item edit form."""
    if needs_login():
        return redirect(url_for('oauth2callback'))
    item = models.Item.query.filter(models.Category.name == category_name,
                                    models.Item.name == item_name).first()
    if item is not None:
        if not is_same_user(item):
            # redirects the user to log in if they're not the owner of the item
            # which will later redirect them back to the main page
            return redirect(url_for('oauth2callback'))
        form = ItemForm(obj=item)
        return render_template('edit_item.html', form=form, item=item)
    return render_template('generic.html',
                           title="Item Not Found",
                           description="We couldn't find that item.",
                           redirect_to_index=False)


@app.route('/catalog/<category_name>/<item_name>/delete', methods=['GET'])
def delete_item(category_name, item_name):
    """Returns a delete confirmation page for the requested item."""
    if needs_login():
        return redirect(url_for('oauth2callback'))
    item = models.Item.query.filter(models.Category.name == category_name,
                                    models.Item.name == item_name).first()

    if item is not None:
        if not is_same_user(item):
            # redirects the user to log in if they're not the owner of the item
            # which will later redirect them back to the main page
            return redirect(url_for('oauth2callback'))
        form = ItemForm(obj=item)
        return render_template('delete_item.html', item=item, form=form)
    return render_template('generic.html',
                           title="Item Not Found",
                           description="We couldn't find that item.",
                           redirect_to_index=False)


@app.route('/catalog/<category_name>/<item_name>/photo/delete', methods=['GET'])
def delete_photo(category_name, item_name):
    """Returns a delete confirmation page for the requested item."""
    if needs_login():
        return redirect(url_for('oauth2callback'))
    item = models.Item.query.filter(models.Category.name == category_name,
                                    models.Item.name == item_name).first()

    if item is not None:
        if not is_same_user(item):
            # redirects the user to log in if they're not the owner of the item
            # which will later redirect them back to the main page
            return redirect(url_for('oauth2callback'))
        # delete the photo and update the DB
        if os.path.isfile(app.config['IMAGE_DIR'] + item.image):
            os.remove(app.config['IMAGE_DIR'] + item.image)
        item.image = ""
        db.session.add(item)
        db.session.commit()
        form = ItemForm(obj=item)
        return render_template('edit_item.html', item=item, form=form)
    return render_template('generic.html',
                           title="Item Not Found",
                           description="We couldn't find that item.",
                           redirect_to_index=False)


@app.route('/item/<id>/delete', methods=['POST'])
def delete_item_post(id):
    """Deletes the requested item and removes stored image."""
    if needs_login():
        return redirect(url_for('oauth2callback'))
    item = models.Item.query.filter_by(id=id).first()
    if item is not None:
        if not is_same_user(item):
            # redirects the user to log in if they're not the owner of the item
            # which will later redirect them back to the main page
            return redirect(url_for('oauth2callback'))

        # delete the image file if there is one
        if (item.image is not None and
                os.path.isfile(app.config['IMAGE_DIR'] + item.image)):
            os.remove(app.config['IMAGE_DIR'] + item.image)

        name = item.name
        db.session.delete(item)
        db.session.commit()
        return render_template('generic.html',
                               title="Delete Completed",
                               description="%s has been deleted." % name,
                               redirect_to_index=True)
    return render_template('generic.html',
                           title="Item Not Found",
                           description="We couldn't find that item.",
                           redirect_to_index=False)


@app.route('/catalog/<name>', methods=['GET'])
def get_category(name):
    """Returns items under the requested category."""
    category = models.Category.query.filter_by(name=name).first()
    if category is not None:
        items = models.Item.query.filter(models.Item.category == category)
        form = CategoryForm(obj=category)
        return render_template('category.html',
                               form=form,
                               category=category,
                               categories=models.Category.query.all(),
                               items=items)
    return render_template('generic.html',
                           title="Category Not Found",
                           description="We couldn't find that category.",
                           redirect_to_index=False)


@app.route('/item/<id>', methods=['POST'])
def update_item(id):
    """Updates the requested item."""
    if needs_login():
        return redirect(url_for('oauth2callback'))
    form = ItemForm(request.form)
    item = models.Item.query.filter_by(id=id).first()
    if not form.validate():
        return render_template('edit_item.html', form=form, item=item)

    # retain the old image path before populate_obj overwrites it with form
    # data
    old_image = item.image
    form.populate_obj(item)
    item.image = old_image

    if form.image is not None:
        image_data = request.files['image'].read()
        if len(image_data) > 0:
            # generate a random file name and save it to the image folder
            filename = ''.join(random.choice(
                string.ascii_uppercase + string.digits) for x in xrange(16))
            ext = os.path.splitext(request.files['image'].filename)[1]
            open(app.config['IMAGE_DIR'] +
                 filename + ext, 'w').write(image_data)
            item.image = filename + ext
            # if the user updates the image, delete the old one
            if os.path.isfile(app.config['IMAGE_DIR'] + old_image):
                os.remove(app.config['IMAGE_DIR'] + old_image)

    db.session.add(item)
    db.session.commit()
    return render_template('generic.html',
                           title="Update Completed",
                           description="%s has been updated." % item.name,
                           redirect_to_index=True)


@app.route('/item/new', methods=['GET'])
def new_item():
    """Returns a new item form."""
    if needs_login():
        return redirect(url_for('oauth2callback'))
    if len(models.Category.query.all()) == 0:
        return render_template('generic.html',
                               title="No Categories",
                               description="You can't add an item until you " +
                               "create a category.",
                               redirect_to_index=False)
    return render_template('new_item.html', form=ItemForm())


@app.route('/item/new', methods=['POST'])
def add_item():
    """Saves the new item and redirects to confirmation page."""
    if needs_login():
        return redirect(url_for('oauth2callback'))
    form = ItemForm(request.form)
    if not form.validate():
        return render_template('new_item.html', form=form)

    image = ""
    if form.image.data is not None:
        image_data = request.files['image'].read()
        if len(image_data) > 0:
            # generate a random file name and save it to the image folder
            filename = ''.join(random.choice(
                string.ascii_uppercase + string.digits) for x in xrange(16))
            ext = os.path.splitext(request.files['image'].filename)[1]
            open(app.config['IMAGE_DIR'] +
                 filename + ext, 'w').write(image_data)
            image = filename + ext

    item = models.Item(name=form.name.data,
                       user=get_current_user(),
                       description=form.description.data,
                       category=form.category.data,
                       image=image)

    db.session.add(item)
    db.session.commit()
    return render_template('generic.html',
                           title="Item Added",
                           description="%s has been added." % item.name,
                           redirect_to_index=True)


@app.route('/category/new', methods=['GET'])
def new_category():
    """Returns a new category form."""
    if needs_login():
        return redirect(url_for('oauth2callback'))
    return render_template('new_category.html', form=CategoryForm())


@app.route('/category/new', methods=['POST'])
def add_category():
    """Saves the new item and redirects to confirmation page."""
    if needs_login():
        return redirect(url_for('oauth2callback'))
    form = CategoryForm(request.form)

    if not form.validate():
        return render_template('new_category.html', form=form)

    category = models.Category(form.name.data)
    db.session.add(category)
    db.session.commit()
    return render_template('generic.html',
                           title="Category Added",
                           description="%s has been added." % category.name,
                           redirect_to_index=True)


@app.route('/catalog.json', methods=['GET'])
def catalog_json():
    """Returns JSON version of the catalog."""
    categories = []
    for category in models.Category.query.all():
        item = category.serialize()
        item['items'] = list(x.serialize() for x in models.Item.query.filter(
            models.Item.category == category))
        categories.append(item)
    result = {}
    result['categories'] = categories
    response = make_response(json.dumps(result,
                                        sort_keys=False,
                                        indent=3,
                                        separators=(',', ': ')),
                             200)
    response.headers['Content-Type'] = 'application/json'
    return response


@app.route('/catalog.atom', methods=['GET'])
def catalog_atom():
    """Returns an RSS feed of the catalog items."""
    # adapted from flask snippets article: http://bit.ly/22pMFDO
    feed = AtomFeed('Recent Items', feed_url=request.url, url=request.url_root)
    items = models.Item.query.order_by(desc(models.Item.created)).all()
    for item in items:
        feed.add(item.name,
                 Markup(render_template("atom_template.html", item=item)),
                 content_type='html',
                 author=item.user.name,
                 url=url_for('item_detail',
                             category_name=item.category.name,
                             item_name=item.name),
                 updated=item.created)
    return feed.get_response()


def needs_login():
    """
    Convenience method to determine if user is logged in.
    """
    if 'credentials' not in session:
        return True
    credentials = client.OAuth2Credentials.from_json(session['credentials'])
    if credentials.access_token_expired:
        return True
    return False


def get_current_user():
    """
    Convenience method to get the current User object from the ID stored
    in the session.
    """
    user = None
    if session.get('user'):
        user = models.User.query.filter_by(user_id=session.get('user')).first()
    return user


def is_same_user(item):
    """
    Convenience method to determine if current user is the owner of the given 
    item.
    """
    if get_current_user() == None or item == None:
        return False
    if item.user.user_id == get_current_user().user_id:
        return True
    return False
