# coding: utf-8

from jnpr.junos import Device
from jnpr.junos.utils.config import Config
from jnpr.junos.exception import LockError
from jnpr.junos import exception as EzErrors
from flask import request, redirect, url_for, render_template, flash
from pyez_flask import app, db
from pyez_flask.models import Entry, Dev
from xml.sax.saxutils import *
from jinja2 import Environment
import pyez_func
import config
import threading
import multiprocessing
import time
import os
import traceback
import bs4


@app.route('/')
def show_entries():
  f = open(config.PYEZ_FLASK_DIR + 'param.txt')
  params = f.read().rstrip().split('\n')

  start_addr = params[0].split(' ')[2]
  end_addr = params[1].split(' ')[2]
  user = params[2].split(' ')[2]
  password = params[3].split(' ')[2]
  
  return render_template('show_entries.html', user=user, password=password, start_addr=start_addr, end_addr=end_addr)


@app.route('/show_devices.html')
def show_devices():
  f = open(config.PYEZ_FLASK_DIR + 'param.txt')
  params = f.read().rstrip().split('\n')
  start_addr = params[0].split(' ')[2]
  end_addr = params[1].split(' ')[2]
  devices_sub = pyez_func.create_addr_list2(start_addr, end_addr)
  
  devices = []
  for device in devices_sub:
    filename = config.PYEZ_DEV_INFO_DIR + 'facts/' + device

    if os.path.exists(filename):
      devices.append(device)

  query_count= len(devices)
  return render_template('show_devices.html', devices=devices, query_count=query_count)


@app.route('/<ip_addr>')
def show_detailed_info(ip_addr):
  '''
  f = open(config.PYEZ_FLASK_DIR + 'host_addr.txt')
  host_addr_list = f.read().rstrip().split('\n')
  '''
  hostname = ""
  try:
    f = open(config.PYEZ_DEV_INFO_DIR + 'facts/' + ip_addr)
    html = f.read()
    soup = bs4.BeautifulSoup(html, "lxml")
    hostname = ' - ' + soup.find(id="host").text + ' - '
  except:
    hostname = ""
  '''
  for host in host_addr_list:
    if ip_addr == host.split(',')[1]:
      hostname = "(" + host.split(',')[0] +  ")"
  f.close()
  '''
  return render_template('detailed_info.html', ip_addr=ip_addr, hostname=hostname)

@app.route('/show_result', methods=['POST'])
def show_result():
  check_list = request.form.getlist('check')
  command = request.form['command']
  files = []
 
  
  if command == '-':
    return redirect(url_for('show_devices'))
  elif command == 'show_vlan_table':
    for ip_addr in check_list:
      files.append('/dev_info/vlans/' + ip_addr)

    return render_template('show_vlans.html', files=check_list)
  
  elif command == 'show_lldp_table':
    for ip_addr in check_list:
      files.append('dev_info/lldp/' + ip_addr)
    return render_template('show_lldp_table.html', files=check_list)

  elif command == 'show_hardware_information':
    return render_template('show_hardware_information.html', files=check_list)


@app.route('/send_commands.html')
def send_commands(conf_diff=''):
  f = open(config.PYEZ_FLASK_DIR + 'param.txt')
  params = f.read().rstrip().split('\n')
  start_addr = params[0].split(' ')[2]
  end_addr = params[1].split(' ')[2]
  devices_sub = pyez_func.create_addr_list2(start_addr, end_addr)
  
  devices = []
  for device in devices_sub:
    filename = config.PYEZ_DEV_INFO_DIR + 'facts/' + device

    if os.path.exists(filename):
      devices.append(device)

  query_count= len(devices)
  diff = conf_diff
  return render_template('send_commands.html', devices=devices, query_count=query_count, diff=diff)

@app.route('/cmd_result', methods=['POST'])
def cmd_result():
  env = Environment(cache_size=0)
  check_list = request.form.getlist('check')
  
  f = open(config.PYEZ_FLASK_DIR + 'param.txt')
  params = f.read().rstrip().split('\n')
  start_addr = params[0].split(' ')[2]
  end_addr = params[1].split(' ')[2]
  devices_sub = pyez_func.create_addr_list2(start_addr, end_addr)
  devices = []
  for device in devices_sub:
    filename = config.PYEZ_DEV_INFO_DIR + 'facts/' + device

    if os.path.exists(filename):
      devices.append(device)

  query_count= len(devices)
  command = request.form['command']
  cmds = command.split('\n')

  diff_list = []
  
  queue = multiprocessing.Queue()

  for ip_addr in check_list:
    cmd_result = multiprocessing.Process(target=send_cmd, args=(ip_addr, cmds, queue))
    cmd_result.start()
  for ip_addr in check_list: 
    diff_list.append(queue.get())

  diff = '\n'.join(diff_list)

  return render_template('send_commands.html', devices=devices, query_count=query_count, diff=diff)
  

@app.route('/install_junos.html')
def install_junos():
  f = open(config.PYEZ_FLASK_DIR + 'param.txt')
  params = f.read().rstrip().split('\n')
  start_addr = params[0].split(' ')[2]
  end_addr = params[1].split(' ')[2]
  devices_sub = pyez_func.create_addr_list2(start_addr, end_addr)
  
  devices = []
  for device in devices_sub:
    filename = config.PYEZ_DEV_INFO_DIR + 'facts/' + device

    if os.path.exists(filename):
      devices.append(device)

  query_count= len(devices)
  
  return render_template('install_junos.html', devices=devices, query_count=query_count)


@app.route('/install', methods=['POST'])
def install_image():
  dev_list = request.form.getlist('file')


  f = open(config.PYEZ_FLASK_DIR + 'param.txt')
  params = f.read().rstrip().split('\n')
  start_addr = params[0].split(' ')[2]
  end_addr = params[1].split(' ')[2]
  devices_sub = pyez_func.create_addr_list2(start_addr, end_addr)
  
  devices = []
  for device in devices_sub:
    filename = config.PYEZ_DEV_INFO_DIR + 'facts/' + device

    if os.path.exists(filename):
      devices.append(device)

  query_count= len(devices)
  
  return render_template('install_junos.html', devices=devices, query_count=query_count)


@app.route('/set_param', methods=['POST'])
def set_param():
  f = open(config.PYEZ_FLASK_DIR + 'param.py', 'w')
  
  start_addr = request.form['start_addr']
  end_addr = request.form['end_addr']
  user = 'lab'
  password = 'lab'
  

  result = '' 
  result += 'start_addr="' + start_addr + '"\n'
  result += 'end_addr="' + end_addr + '"\n'
  result += 'user="' + user + '"\n'
  result += 'password="' + password + '"\n'

  f.write(result)
  f.close()

  return redirect(url_for('show_entries'))

@app.route('/collect', methods=['POST'])
def collect_dev_info():

  start_addr = request.form['start_addr']
  end_addr = request.form['end_addr']
  user = request.form['user']
  password = request.form['password']
 
  

  if request.form['button'] == 'Search':
    f = open(config.PYEZ_FLASK_DIR + 'param.txt', 'w')
    
  
    result = '' 
    result += 'start_addr = ' + start_addr + '\n'
    result += 'end_addr = ' + end_addr + '\n'
    result += 'user = ' + user + '\n'
    result += 'password = ' + password + '\n'
  
    f.write(result)
    f.close()

    if os.path.isfile(config.PYEZ_FLASK_DIR + 'host_addr.txt'):
      os.remove(config.PYEZ_FLASK_DIR + 'host_addr.txt')
    
    addr_list = pyez_func.create_addr_list2(start_addr, end_addr)
    
    for addr in addr_list:
      mp = multiprocessing.Process(target=pyez_func.host_to_addr, args=(addr, user, password))
      mp.start()
    '''
    host_addr_list = []
    queue = multiprocessing.Queue()

    addr_list = pyez_func.create_addr_list2(start_addr, end_addr)
    
    for addr in addr_list:
      mp = multiprocessing.Process(target=host_to_addr, args=(addr, user, password, queue))
      mp.start()



    #for addr in addr_list:
    while not queue.empty():
      host_addr_list.append(queue.get())

    result = '\n'.join(host_addr_list)
    print result

    f = open(config.PYEZ_FLASK_DIR + 'host_addr.txt', 'w')
    f.write(result)
    f.close()
    '''

    return redirect(url_for('show_entries'))

  if os.path.isfile(config.PYEZ_FLASK_DIR + 'host_addr.txt') == False:
    return redirect(url_for('show_entries'))


  start_addr = request.form['start_addr']
  end_addr = request.form['end_addr']
  user = request.form['user'] 
  password = request.form['password']
  if pyez_func.check_addr_range(start_addr, end_addr) == False:
    return redirect(url_for('show_entries'))

  Dev.query.delete()
  db.session.commit()

  start = time.time()
 
  f = open(config.PYEZ_FLASK_DIR + 'host_addr.txt', 'r')
  addr_list = f.read().rstrip().split('\n')
  print addr_list

  for addr in addr_list:
 
    mp = multiprocessing.Process(target=pyez_func.get_device_information2, args=(addr.split(',')[1], user, password))
    mp.start()
   
  print time.time() - start 
  return redirect(url_for('show_entries'))

def send_cmd(ip_addr, cmds, queue):

  if cmds == []:
    return 

  f = open(config.PYEZ_FLASK_DIR + 'param.txt')
  params = f.read().rstrip().split('\n')

  start_addr = params[0].split(' ')[2]
  end_addr = params[1].split(' ')[2]
  user = params[2].split(' ')[2]
  password = params[3].split(' ')[2]
  
  dev = pyez_func.call_dev(ip_addr, user, password)
  
  try:
    dev.open(gather_facts=False)

  except:
    return 'could not connect' 
 
  cfg = Config(dev)

  device_addr = "----------" + ip_addr + "----------"
  try:
    cfg.lock()
    for cmd in cmds:
      cmd_sub = cmd.rstrip()
      cfg.load(cmd_sub, format="set")

    result = cfg.diff()
    cfg.commit()
    print 'commit'
    queue.put(device_addr + result)
  except:
    print 'error'
    queue.put(device_addr + '\n' + 'unknown command')

  finally:
    cfg.unlock()

  return


def host_to_addr(ip_addr, user, password, queue):
  dev = pyez_func.call_dev(ip_addr, user, password)

  try:
    dev.open()
  except:

    if os.path.isfile(config.PYEZ_DEV_INFO_DIR + 'facts/' + ip_addr):
      os.remove(config.PYEZ_DEV_INFO_DIR + 'facts/' + ip_addr)

    if os.path.isfile(config.PYEZ_DEV_INFO_DIR + 'vlans/' + ip_addr):
      os.remove(config.PYEZ_DEV_INFO_DIR + 'vlans/' + ip_addr)

    if os.path.isfile(config.PYEZ_DEV_INFO_DIR + 'lldp/' + ip_addr):
      os.remove(config.PYEZ_DEV_INFO_DIR + 'lldp/' + ip_addr)

    if os.path.isfile(config.PYEZ_DEV_INFO_DIR + 'fig/' + ip_addr):
      os.remove(config.PYEZ_DEV_INFO_DIR + 'fig/' + ip_addr)

    if os.path.isfile(config.PYEZ_DEV_INFO_DIR + 'hardware/' + ip_addr):
      os.remove(config.PYEZ_DEV_INFO_DIR + 'hardware/' + ip_addr)
    return
  
  dev_dict = dev.facts

  queue.put(str(dev_dict.get('hostname')) + ',' + ip_addr)
  return
