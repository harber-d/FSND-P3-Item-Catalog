Item Catalog
============

### Before you get started
* Make sure you have a google account to log into the catalog; should be easy for Udacity staff :-)

### How to get started
Unzip the file and set up your Vagrant machine:
```
$ unzip project_3.zip
$ cd vagrant
$ vagrant up
$ vagrant ssh
```

Set up the database:
```
$ cd /vagrant/catalog
$ python db_create.py
```

Start the Flask application:
```
$ python run.py
```

Navigate to the application your browser at: http://localhost:5000/

Enjoy!