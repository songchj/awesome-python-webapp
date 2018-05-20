#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time, uuid, functools, threading, logging, mysql.connector


class Dict(dict):
    
    def __init__(self, name=(), values=(), **kw):
        super(Dict,self).__init__(**kw)
        for k , v in zip(name, values):
            self[k] = v
    
    def __setattr__(self, key, value):
        self[key] = value

    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(r"'Dict' object has no attribute '%s'" % key)

def next_id(t=None):
    if t is None:
        t = time.time()
    return '%015d%s000' % (int(t * 1000), uuid.uuid4().hex)

def _profiling(start, sql=''):
    t = time.time()
    if t > 0.1:
        logging.warning('[PROFILINT] [DB] %s: %s' % (t, sql))
    else:
        logging.info('[PROFILING] [DB] %s: %s' % (t, sql))



class DBError(Exception):
    pass

class MultiColumsError(DBError):
    pass

class _LasyConnection(object):
    def __init__(self):
        self.connection = None

    def cursor(self):
        if self.connection is None:
            config = { 'user': 'root','password': 'password','database': 'test' }
            connection = mysql.connector.connect(**config)
            logging.info('open connection <%s>...' % hex(id(connection)))
            self.connection = connection
        return self.connection.cursor()

    def commit(self):
        self.connection.commit()
    
    def rollback(self):
        self.connection.rollback()
    
    def cleanup(self): 
        if self.connection:
            connection = self.connection
            self.connection = None
            logging.info('close connection <%s>...' % hex(id(connection)))
            connection.close()

# 持有数据库连接的上下文对象：
class _DbCtx(threading.local):
    def __init__(self):
        self.connection = None
        self.transactions = 0
    
    def is_init(self):
        return not self.connection is None

    def init(self):
        logging.info('open lazy connection...')
        self.connection = _LasyConnection()
        self.transactions = 0
    
    def cleanup(self):
        self.connection.cleanup()

    def cursor(self):
        return self.connection.cursor()

_db_ctx = _DbCtx()
engine = None
#数据库引擎对象：
class _Engine(object):
    def __init__(self, connect):
        self._connect = connect
    
    def connect(self):
        return self._connect

#没有用到这个函数，没有理解廖大神的精髓，按照他的写法，每次执行第二次sql语句的时候都会报错，
# 因为第一次执行完sql语句，把connection给关掉了
def create_engine(user, password, database, host='127.0.0.1', port=3306, **kw):
    global engine
    if engine is not None:
        raise DBError('Engine is already initialized.')
    config = { 'user': 'root','password': 'password','database': 'test' }
    cnx = mysql.connector.connect(**config)
    engine = _Engine(cnx)
    # test connection...
    logging.info('Init mysql engine <%s> ok.' % hex(id(engine)))
    

class _ConnectionCtx(object):
    def __enter__(self):
        global _db_ctx
        self.should_cleanup = False
        if not _db_ctx.is_init():
            _db_ctx.init()
            self.should_cleanup = True
        return self
    
    def __exit__(self, exctype, excvalue, traceback):
        global _db_ctx
        if self.should_cleanup:
            _db_ctx.cleanup()

def connection():
    return _ConnectionCtx()

def with_connection(func):
    @functools.wraps(func)
    def _wrapper(*args, **kw):
        with _ConnectionCtx():
            return func(*args, **kw)
    return _wrapper

class _TransactionCtx(object):
    def __enter__(self):
        global _db_ctx
        self.should_close_conn = False
        if not _db_ctx.is_init():
            _db_ctx.init()
            self.should_close_conn = True
        _db_ctx.transactions = _db_ctx.transactions + 1
        logging.info('begin transaction...' if _db_ctx.transactions==1 else 'join current transaction...')
        return self

    def __exit__(self, exctype, exvalue, traceback):
        global _db_ctx
        _db_ctx.transactions = _db_ctx.transactions - 1
        try:
            if _db_ctx.transactions == 0:
                if exctype is None:
                    self.commit()
                else:
                    self.rollback()
        finally:
            if self.should_close_conn:
                _db_ctx.cleanup()
    
    def commit(self):
        global _db_ctx
        logging.info('commit transaction...')
        try:
            _db_ctx.connection.commit()
            logging.info('commit ok.')
        except:
            logging.warning('commit failed. try rollback...')
            _db_ctx.connection.rollback()
            logging.warning('rollback ok.')
            raise
    
    def rollback(self):
        global _db_ctx
        logging.warning('rollback transaction...')
        _db_ctx.connection.rollback()
        logging.info('rollback ok.')

def transaction():
    return _TransactionCtx()

def with_transaction(func):
    @functools.wraps(func)
    def _wrapper(*args, **kw):
        with _TransactionCtx():
            return func(*args, **kw)
    return _wrapper
       


def _select(sql, first, *args):
    global _db_ctx
    cursor = None
    sql  = sql.replace('?', '%s')
    logging.info('SQL: %s, ARGS: %s' % (sql, args))
    try:
        cursor = _db_ctx.connection.cursor()
        cursor.execute(sql, args)
        if cursor.description:
            names = [x[0] for x in cursor.description]
        if first:
            values = cursor.fetchone()
            print values
            if not values:
                return None
            return [Dict(names, values)]
        temp =  cursor.fetchall()
        print temp
        return [Dict(names, x) for x in temp]
    finally:
        if cursor:
            cursor.close()

@with_connection
def select_one(sql, *args):
    return _select(sql, True, *args)

@with_connection
def select_int(sql, *args):
    d = _select(sql, True, *args)
    '''修改了廖大神的原始代码，在_select中取一条数据时返回的是一个dict，至少有id、name、email等必配的参数
    必然不会等于1，所以把他改成列表了，然后这里就只能用d[0]获取对应的字典
    '''
    if len(d) != 1:
        raise MultiColumsError('Expect only one column')
    return d[0].values()[0]

@with_connection
def select(sql, *args):
    return _select(sql, False, *args)

@with_connection
def _update(sql, *args):
    global _db_ctx
    cursor = None
    sql  = sql.replace('?', '%s')
    logging.info('SQL: %s, ARGS: %s' % (sql, args))
    try:
        cursor = _db_ctx.cursor()
        cursor.execute(sql, args)  
        r = cursor.rowcount
        if _db_ctx.transactions == 0:
            logging.info('auto commit')
            _db_ctx.connection.commit()
        return r
    finally:
        if cursor:
            cursor.close()

def insert(table, **kw):
    cols, args = zip(*kw.iteritems())
    sql = 'insert `%s` (%s) values (%s)' % (table, ','.join(['`%s`' % col for col in cols]),
            ','.join(['?' for i in range(len(cols))]))
    return _update(sql, *args)

def update(sql, *args):
    return _update(sql, *args)

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)       
    create_engine('root', 'password', "test")
    select('select * from user')
    update('update user set name=? where id=?', 'song', '1')
    select_one('select * from user where id = %s', 1)
    update('update user set name=? where id=?', 'wei', '2')
    select_int('select * from user where id = %s', 2)
    insert('user', id=5, name='Linux')
    insert('user', id=6, name='Git')
    select('select * from user')