#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging

from transwarp.web import get, view

from models import User, Blog, Comment

print "urls.py"

@view('blogs.html')
@get('/')
def test_user():
    blogs = Blog.find_all()  
    user = User.find_first('where email=?', 'admin@example.com')
    return dict(blogs=blogs, user=user)