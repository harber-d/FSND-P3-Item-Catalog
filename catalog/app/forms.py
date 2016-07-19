from wtforms import TextField, TextAreaField, validators
from wtforms.ext.sqlalchemy.fields import QuerySelectField
from app.models import Category
from flask_wtf import Form
from flask_wtf.file import FileField


class ItemForm(Form):
    """Form containing catalog item fields"""
    name = TextField('Item Name',
                     [validators.required(),
                      validators.Length(min=1, max=250)])
    description = TextAreaField('Description',
                                [validators.Length(min=0, max=2000)])
    category = QuerySelectField('Category',
                                query_factory=lambda: Category.query.all(),
                                validators=[validators.required()])
    image = FileField('Image')


class CategoryForm(Form):
    """Form containing catalog category fields"""
    name = TextField('Category Name',
                     [validators.required(),
                      validators.Length(min=3, max=25)])
