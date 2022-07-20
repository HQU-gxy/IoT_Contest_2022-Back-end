#!/usr/bin/python3
import pymysql
from datetime import datetime
import time
import threading
import json
from bottle import *

db = pymysql.connect(host='localhost', user='fucker',
                     passwd='2333', db='library')
cursor = db.cursor()


def gen_id():
    cursor.execute("SELECT MAX(id) FROM users")
    id = cursor.fetchone()[0]
    if id == None:
        return 1
    else:
        return id+1


@route('/login', method='POST')
def login():
    args = request.forms
    username = args.get('userName')
    password = args.get('passwd')
    if cursor.execute('select * from users where username=%s', (username)):
        if cursor.execute(
                'select id from users where username=%s and pswd=password(%s)', (username, password)):
            userId = cursor.fetchone()[0]
            return '{"status": "SUC","userId": %s}' % userId
        else:
            return '{"status": "INV_PASS"}'

    else:
        return '{"status": "NO_USER"}'


@route('/register', method='POST')
def register():
    args = request.forms
    username = args.get('userName')
    password = args.get('passwd')
    if cursor.execute('select * from users where username=%s', (username)):
        return '{"status":"USER_EXIST"}'
    else:
        id = gen_id()
        cursor.execute(
            'insert into users(username, pswd,id) values(%s, password(%s),%s)', (username, password, id))

        db.commit()
        return '{"status":"SUC", "userId":'+str(id)+'}'


@route('/seat_status')
def seat_status():
    userId = int(request.query['userid'])
    cursor.execute('select * from seats')
    stats = cursor.fetchall()
    if stats:
        statusArray = []
        for stat in stats:
            if stat[1] == 2:  # seat is reserved
                cursor.execute(
                    'select id from reservations where seat_num=%s', (stat[0]))

                # user is the one who reserved the seat
                if cursor.fetchone()[0] == userId:
                    statusArray.append({'seatNum': stat[0], 'status': 3})
                else:
                    statusArray.append({'seatNum': stat[0], 'status': 2})

            else:
                statusArray.append({'seatNum': stat[0], 'status': stat[1]})

        statusJson = json.dumps({'valid': True, 'seats': statusArray})
        return statusJson
    else:
        return '{"valid":false}'


@route('/reserve', method='POST')
def reserve():
    args = request.forms
    userId = args.get('userId')
    seatNum = args.get('seatNum')
    cursor.execute('select * from seats where seat_num=%s', (seatNum))
    if cursor.fetchone()[1] == 0:  # seat is available
        cursor.execute(
            'update seats set status=2 where seat_num=%s', (seatNum))

        cursor.execute('insert into reservations(id,seat_num,reserve_dt) values(%s,%s,%s)',
                       (userId, seatNum, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

        db.commit()
        return 'SUC'
    else:
        return 'OCCUPIED'


@route('/cancel', method='POST')
def cancel():
    args = request.forms
    userId = args.get('userId')
    seatNum = args.get('seatNum')

    if cursor.execute(
            'select * from reservations where seat_num=%s and id=%s', (seatNum, userId)):

        cursor.execute(
            'update seats set status=0 where seat_num=%s', (seatNum))
        cursor.execute('delete from reservations where seat_num=%s',
                       (seatNum))
        db.commit()
        return 'SUC'
    else:
        return 'UNRESERVED'


@route('/change_status', method='POST')
def change_status():
    args = json.loads(request.body)
    seatNum = args['seatNum']
    status = args['status']
    print(seatNum, status)
    if cursor.execute('select * from seats where seat_num=%s', (seatNum)):

        cursor.execute(
            'update seats set status=%s where seat_num=%s', (status, seatNum))
        db.commit()
        return 'SUC'
    else:
        return 'INV_SEAT'


class checkReservationExpireThread(threading.Thread):
    def run(self):
        while True:
            time.sleep(10)
            cursor.execute('select * from reservations')
            reservations = cursor.fetchall()
            for reservation in reservations:
                reserve_dt = reservation[2]
                if reserve_dt + timedelta(minutes=15) < datetime.now():
                    cursor.execute(
                        'update seats set status=0 where seat_num=%s', (reservation[0]))
                    cursor.execute('delete from reservations where seat_num=%s',
                                   (reservation[0]))
                    db.commit()
                    print('reservation expired')


checkReservationExpireThread().start()

try:
    run(host='0.0.0.0', port=2333)

except pymysql.err.InterfaceError:
    db = pymysql.connect(host='localhost', user='fucker',
                         passwd='2333', db='library')
    cursor = db.cursor()

finally:
    db.close()
    exit()
