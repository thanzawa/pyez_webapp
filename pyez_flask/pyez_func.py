# coding: utf-8
from jnpr.junos import Device
from jnpr.junos.utils.config import Config
from jnpr.junos.exception import LockError
from jnpr.junos import exception as EzErrors
from pyez_flask import app, db
from pyez_flask.models import Entry, Dev
from more_itertools import chunked
from lxml import etree
import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.pylab as plt

import numpy as np
import mpld3
from mpld3 import utils, plugins


import sys,os
import config, param
import time
import traceback
import shutil



Device.auto_probe = 1 
#Device.timeout = 1
#gather_facts




def call_dev(ip_addr, user, password):

  dev = Device(host=ip_addr, user=user, password=password)
  

  return dev

def host_to_addr(ip_addr, user, password):
  dev = call_dev(ip_addr, user, password)

  try:
    dev.open()
  except:
    return

  dev_dict = dev.facts
  filename = config.PYEZ_FLASK_DIR + 'host_addr.txt'
  f = open(filename, 'a')
  f.write(str(dev_dict.get('hostname')) + ',' + ip_addr + '\n')
  f.close()
  dev.close()


def get_device_information2(ip_addr, user, password):

  dev = call_dev(ip_addr, user, password)
  print ip_addr
  try:
    dev.open()
  except:
    print 'could not connect'
    if os.path.isfile(config.PYEZ_DEV_INFO_DIR + 'facts/' + ip_addr):
      os.remove(config.PYEZ_DEV_INFO_DIR + 'facts/' + ip_addr)

    if os.path.isfile(config.PYEZ_DEV_INFO_DIR + 'vlans/' + ip_addr):
      os.remove(config.PYEZ_DEV_INFO_DIR + 'vlans/' + ip_addr)

    if os.path.isfile(config.PYEZ_DEV_INFO_DIR + 'lldp/' + ip_addr):
      os.remove(config.PYEZ_DEV_INFO_DIR + 'lldp/' + ip_addr)

    if os.path.isfilr(config.PYEZ_DEV_INFO_DIR + 'fig/' + ip_addr):
      os.remove(config.PYEZ_DEV_INFO_DIR + 'fig/' + ip_addr)

    return None

  dev_dict = dev.facts

  '''
  filename = config.PYEZ_FLASK_DIR + 'host_addr.txt'
  f = open(filename, 'a')
  f.write(str(dev_dict.get('hostname')) + ',' + ip_addr + '\n')
  f.close()
  '''

  result = ''
  #result += '<th><input type="checkbox" name="check" value=' + ip_addr + '></th>'
  result += '<th><a href="./' + ip_addr + '">' + ip_addr + '</a></th>'
  result += '<th>' + str(dev_dict.get('hostname')) + '</th>'
  result += '<th>' + str(dev_dict.get('model')) + '</th>'
  result += '<th>' + str(dev_dict.get('version')) + '</th>'


  filename = config.PYEZ_DEV_INFO_DIR + 'facts/' + ip_addr 
  f = open(filename, 'w')
  f.write(result)
  f.close()


  create_vlan_table(dev, ip_addr)
  create_lldp_table(dev, ip_addr, str(dev_dict.get('hostname')))
  dev.close()



def get_device_information(ip_addr):
  dev = call_dev(ip_addr, user, password)
   
  try:
    dev.open()

  except:
    print 'could not connect'
    return None
  
  dev_dict = dev.facts
  if dev.facts == {}:
    dev.close()
    return None


  if 'hostname' in dev_dict == False:
    dev_dict['hostname'] = "" 
  
  
  device = Dev(
            ip_addr = ip_addr,
            hostname = dev_dict.get('hostname'),
            model = dev_dict.get('model'),
            serial_num = dev_dict.get('serialnumber'),
            os_version = dev_dict.get('version'),
            ip_addr_int = addr_to_i(ip_addr) 
          )
  
  db.session.add(device)
  db.session.commit()
  
  create_vlan_table(dev, ip_addr)
  dev.timeout = 60
  dev.close()

def register_dev(dev_dict, addr):

  dev = Dev(
          ip_addr = addr,
          hostname = dev_dict['hostname'],
          model = dev_dict['model'],
          serial_num = dev_dict['serialnumber'],
          os_version = dev_dict['version']
        )
  db.session.add(dev)
  db.session.commit()

def get_register_dev(ip_addr):
  dev_dict = get_device_information(ip_addr)

  if dev_dict != None:
    register_dev(dev_dict, ip_addr)




def get_vlans_xml(dev, ip_addr, filename):
  result = dev.rpc.get_vlan_information()

  f = open(filename, 'w')
  f.write(etree.tostring(result))
  f.close()


def create_vlan_table(dev, ip_addr):
  result = '<table class="table table-striped"><tr><th>VLAN Name</th><th>VLAN ID</th><th>Interfaces</th></tr>\n' 

  try:
    rpc_elem = dev.rpc.get_vlan_information()
  except:
    return
  
  rpc_response = etree.tostring(rpc_elem)
  root = etree.fromstring(rpc_response)
  
  model = dev.facts['model']
  tag = ''

  if root.find('vlan') is not None:
    vlan_entries = root.xpath('//vlan')
  else:
    vlan_entries = root.xpath('//l2ng-l2ald-vlan-instance-group')
    tag = 'l2ng-l2rtb-'


  for vlan in vlan_entries:
    vlan_name = vlan.find(tag + 'vlan-name').text
    vlan_id = vlan.find(tag + 'vlan-tag').text
    member_ifs = vlan.xpath('descendant::' + tag + 'vlan-member-interface')
    if_num = len(member_ifs)

    result += '<tr><td rowspan=' + str(if_num) + '>' + vlan_name + '</td>'
    result += '<td rowspan=' + str(if_num) + '>' + vlan_id + '</td>\n' 
    i = 0
    for member_if in member_ifs:
      if isinstance(member_if.text, str):
        if_text = member_if.text
      else:
        if_text = 'None' 

      if i == 0:
        result += '<td>' + if_text + '</td></tr>\n'
      else:
        result += '<tr><td>' + if_text + '</td></tr>\n'

      i += 1

  result += '</table>'
  
  f = open(config.PYEZ_DEV_INFO_DIR + 'vlans/' + ip_addr, 'w')
  f.write(result)
  f.close()

  print 'VLAN table created' 



def create_lldp_table(dev, ip_addr, hostname):
  result = '<table class="table table-striped">\n<tr>\n<th>Local Interface</th>\n<th>Remote Hostname</th>\n<th>Remote Interfaces</th>\n</tr>\n'
 
  try:
    rpc_response = etree.tostring(dev.rpc.get_lldp_neighbors_information())
  
    root = etree.fromstring(rpc_response)
    entries = root.xpath('//lldp-neighbor-information')
    neighbors = []
    
    port_dict = {}
    


    for entry in entries:
      lldp_dict = {}
      lldp_dict["local_i"] = ""
      lldp_dict["remote_host"] = ""
      lldp_dict["remote_port"] = ""


      if entry.find('lldp-local-interface') is not None:
        lldp_dict["local_i"] = entry.find('lldp-local-interface').text
      elif entry.find('lldp-local-port-id') is not None:
        lldp_dict["local_i"] = entry.find('lldp-local-port-id').text
      
      if entry.find('lldp-remote-system-name') is not None:
        lldp_dict["remote_host"] = entry.find('lldp-remote-system-name').text
        neighbors.append(entry.find('lldp-remote-system-name').text)
      elif entry.find('lldp-remote-chassis-id') is not None and entry.find('lldp-remote-chassis-id-subtype') is not None and entry.find('lldp-remote-chassis-id-subtype').text == 'Mac address':
        lldp_dict["remote_host"] = entry.find('lldp-remote-chassis-id').text
        neighbors.append(entry.find('lldp-remote-chassis-id').text)
      else:
        lldp_dict["remote_host"] = ""

      if entry.find('lldp-remote-port-description') is not None:
        lldp_dict["remote_port"] = entry.find('lldp-remote-port-description').text
      elif entry.find('lldp-remote-port-id') is not None:
        lldp_dict["remote_port"] = entry.find('lldp-remote-port-id').text
        #neighbors.append(entry.find('lldp-remote-port-id').text)
      elif entry.find('lldp-remote-chassis-id') is not None and entry.find('lldp-remote-chassis-id-subtype') is not None and entry.find('lldp-remote-chassis-id-subtype').text == 'Mac address':
        lldp_dict["remote_host"] = entry.find('lldp-remote-chassis-id').text
      else:
        lldp_dict["remote_port"] = ""
      
      print lldp_dict.get("remote_host")
      result += '<tr>\n<td>' + lldp_dict["local_i"] + '</td>\n'
      result += str(get_ip_addr(lldp_dict.get('remote_host')))
      #result += '<td><a href="./' + str(get_ip_addr(lldp_dict.get('remote_host'))) + '">' + lldp_dict["remote_host"] + '</td>\n' 
      result += '<td>' + lldp_dict["remote_port"] + '</td>\n</tr>\n'
   
     
      if port_dict.get(str(lldp_dict.get("remote_host"))) is None:
        port_dict[str(lldp_dict.get("remote_host"))] = [[lldp_dict.get("local_i"), lldp_dict.get("remote_port")]]
      else:
        port_dict[str(lldp_dict.get("remote_host"))].append([lldp_dict.get("local_i"), lldp_dict.get("remote_port")])
      
    

    if len(entries) == 0:
      result += '<tr>\n<td colspan="3">None</td>\n</tr>'

    result += '</table>\n'
    print "++++dict+++"
    print port_dict
  

    if neighbors != []:
      create_neighbors_fig_mpld3(hostname, neighbors, ip_addr, port_dict)
    elif neighbors == [] and os.path.isfile(config.PYEZ_DEV_INFO_DIR + 'fig/' + ip_addr):
      os.remove(config.PYEZ_DEV_INFO_DIR + 'fig/' + ip_addr)
  
  
  except EzErrors.RpcError:
    result += '<tr>\n<td colspan="3">lldp service is not runnning</td>\n</tr>\n</table>'
    if os.path.isfile(config.PYEZ_DEV_INFO_DIR + 'fig/' + ip_addr):
      os.remove(config.PYEZ_DEV_INFO_DIR + 'fig/' + ip_addr)
  except EzErrors.ConnectClosedError:
    result += '<tr>\n<td colspan="3">Connection unexpectedly closed</td>\n</tr>\n</table>'
    
    if os.path.isfile(config.PYEZ_DEV_INFO_DIR + 'fig/' + ip_addr):
      os.remove(config.PYEZ_DEV_INFO_DIR + 'fig/' + ip_addr)

  #returr result

  f = open(config.PYEZ_DEV_INFO_DIR + 'lldp/' + ip_addr, 'w')
  f.write(result)
  f.close()

  #if len(entries) != 0:
    #get_neighbors(ip_addr)


def get_neighbors_fig(ip_addr):
  #if os.path.isfile(config.PYEZ_DEV_INFO_DIR + 'fig/' + ip_addr + '.png') == True:
  if os.path.isfile(config.PYEZ_FLASK_DIR + 'static/' + ip_addr + '.png') == True:

    return [ip_addr + '.png']
    #return [config.PYEZ_DEV_INFO_DIR + 'fig/' + ip_addr + '.png']
  else:
    return []


def create_neighbors_fig(hostname, neighbors, ip_addr):
  nodes = neighbors[:]
  nodes.append(hostname)

  node_list1 = [hostname]
  node_list2 = neighbors[:]


  G = nx.Graph()
  G.add_nodes_from(nodes)
  colors = []
  
  colors.append('r')
  for neighbor in neighbors:
    G.add_edge(hostname, neighbor)
    colors.append('#8fc5ff')
  
  print colors

  #pos = nx.circular_layout(G)
  pos = nx.spring_layout(G)
  #edge_labels = {(a, b):'5',(a, c):5, (a, d):5, (a, e):5, (a, f):5}
  
  nx.draw_networkx_nodes(G, pos, node_size=500, node_color=colors)
  #nx.draw_networkx_nodes(G, pos, nodelist=node_list2, node_size=500, node_color='#8fc5ff')
  #nx.draw_networkx_nodes(G, pos, node_size=500, node_color="#8fc5ff")
  nx.draw_networkx_edges(G, pos, width=1)
  #nx.draw_networkx_edge_labels(G, pos,edge_labels)
  nx.draw_networkx_labels(G, pos ,font_size=16, font_color="#000000")
  #nx.draw_networkx_labels(G, pos ,font_size=16, font_color="#ff1500")
  
  plt.xticks([])
  plt.yticks([])
  plt.savefig(config.PYEZ_FLASK_DIR + 'static/' + ip_addr + '.png')
  print "-----fig-----"



'''
def create_neighbors_fig(hostname, neighbors, ip_addr):
  nodes = []
  for neighbor in neighbors:
    nodes.append(neighbor)

  nodes.append(hostname)

  G = nx.Graph()
  #G.add_node(hostname)
  #G.add_nodes_from(nodes)
  G.add_nodes_from(nodes)
  #G.add_nodes_from(neighbors)
  colors = []
  
  colors.append('r')
  for neighbor in neighbors:
    G.add_edge(hostname, neighbor)
    colors.append('#8fc5ff')
  
  print colors

  pos = nx.spring_layout(G)
  #edge_labels = {(a, b):'5',(a, c):5, (a, d):5, (a, e):5, (a, f):5}
  
  nx.draw_networkx_nodes(G, pos, node_size=500, node_color=colors)
  #nx.draw_networkx_nodes(G, pos, node_size=500, node_color="#8fc5ff")
  nx.draw_networkx_edges(G, pos, width=1)
  #nx.draw_networkx_edge_labels(G, pos,edge_labels)
  nx.draw_networkx_labels(G, pos ,font_size=16, font_color="#000000")
  #nx.draw_networkx_labels(G, pos ,font_size=16, font_color="#ff1500")
  
  plt.xticks([])
  plt.yticks([])
  plt.savefig(config.PYEZ_FLASK_DIR + 'static/' + ip_addr + '.png')
  print "-----fig-----"
'''  

def create_addr_list2(start_addr, end_addr):
  end_addr_split = end_addr.split('.')
  
  addr = start_addr

  result = []
  result.append(addr)
  
  if start_addr == end_addr:
    return [start_addr]
  
  while True:
    
    addr_split = addr.split('.')
    addr_int = map(int, addr_split)

    if addr_int[3] == 255 and addr_int[2] == 255 and addr_int[1] == 255 and addr_int[0] == 255:
      break
    elif addr_int[3] == 255 and addr_int[2] == 255 and addr_int[1] == 255 and addr_int[0] != 255:
      addr_int[3] = 0
      addr_int[2] = 0
      addr_int[1] = 0
      addr_int[0] += 1

    elif addr_int[3] == 255 and addr_int[2] == 255 and addr_int[1] != 255:
      addr_int[3] = 0
      addr_int[2] = 0
      addr_int[1] += 1

    elif addr_int[3] == 255 and addr_int[2] != 255:
      addr_int[3] = 0
      addr_int[2] += 1
    else:
      addr_int[3] += 1

    addr_str = map(str, addr_int)
    addr = '.'.join(addr_str)
    
    result.append(addr)

    if addr_str == end_addr_split:
      break

  return result
  



def create_addr_list(start_addr='192.168.1.1', end_addr='192.168.1.2'):
  end_addr_split = end_addr.split('.')
  
  addr = start_addr

  f = open(config.PYEZ_FLASK_DIR + 'addr_list.txt', 'w')
  f.write(addr + '\n')
  if start_addr == end_addr:
    f.close()
    return
  
  while True:
    
    addr_split = addr.split('.')
    addr_int = map(int, addr_split)

    if addr_int[3] == 255 and addr_int[2] == 255 and addr_int[1] == 255 and addr_int[0] == 255:
      break
    elif addr_int[3] == 255 and addr_int[2] == 255 and addr_int[1] == 255 and addr_int[0] != 255:
      addr_int[3] = 0
      addr_int[2] = 0
      addr_int[1] = 0
      addr_int[0] += 1

    elif addr_int[3] == 255 and addr_int[2] == 255 and addr_int[1] != 255:
      addr_int[3] = 0
      addr_int[2] = 0
      addr_int[1] += 1

    elif addr_int[3] == 255 and addr_int[2] != 255:
      addr_int[3] = 0
      addr_int[2] += 1
    else:
      addr_int[3] += 1

    addr_str = map(str, addr_int)
    addr = '.'.join(addr_str)
    
    f.write(addr + '\n')

    if addr_str == end_addr_split:
      break
  
  f.close()


def get_split_list(addr_list, n):
  return list(chunked(addr_list, len(addr_list) / n + 1))

def addr_to_i(addr):
  addr_list = addr.split('.')
  result = []
  for i in addr_list:
    result.append(i.zfill(3))

  return "".join(result)

def check_addr_range(start, end):

  if start.count('.') != 3 or end.count('.') != 3:
    return False

  if addr_to_i(start) > addr_to_i(end):
    return False

  start_val = start.split('.')
  end_val = end.split('.')

  for val in start_val:
    if val.isdigit() == False:
      return False

    if int(val) < 0 or int(val) > 255:
      return False

  for val in end_val:
    if val.isdigit() == False:
      return False

    if int(val) < 0 or int(val) > 255:
      return False
  return True


def get_ip_addr(hostname):
  result = '<td>'
  
  f = open(config.PYEZ_FLASK_DIR + 'host_addr.txt', 'r')
  hosts = f.read().split('\n')
  for host in hosts:
    if hostname == host.split(',')[0]:
      result += '<a href="./' + host.split(',')[1].rstrip() + '">' + hostname + '</td>\n'
      return result
  
  result += hostname + '</td>\n'
  return result

def get_ip_addr2(hostname):
  f = open(config.PYEZ_FLASK_DIR + 'host_addr.txt', 'r')
  hosts = f.read().split('\n')
  for host in hosts:
    if hostname == host.split(',')[0]:
      result = host.split(',')[1].rstrip()
      return result

  return 'javascript:void(0)'


def create_neighbors_fig_mpld3(hostname, neighbors, ip_addr, port_dict):
  
  class ClickInfo(plugins.PluginBase):
    """Plugin for getting info on click"""
    
    JAVASCRIPT = """
    mpld3.register_plugin("clickinfo", ClickInfo);
    ClickInfo.prototype = Object.create(mpld3.Plugin.prototype);
    ClickInfo.prototype.constructor = ClickInfo;
    ClickInfo.prototype.requiredProps = ["id", "urls"];
    function ClickInfo(fig, props){
        mpld3.Plugin.call(this, fig, props);
    };
    
    ClickInfo.prototype.draw = function(){
        var obj = mpld3.get_element(this.props.id);
        urls = this.props.urls;
        obj.elements().on("mousedown",
                          function(d, i){window.location.href = urls[i];});
    }
    """
    def __init__(self, points, urls):
        self.dict_ = {"type": "clickinfo",
                      "id": utils.get_id(points),
                      "urls": urls}
      
  #nodes = []
  #for neighbor in neighbors:
  #  nodes.append(neighbor)
  nodes = neighbors[:]
  nodes.append(hostname)

  #node_list1 = [hostname]
  #node_list2 = neighbors[:]

  G = nx.Graph()
  G.add_nodes_from(nodes)
  colors = []

  
  for neighbor in neighbors:
    G.add_edge(hostname, neighbor)
  
  pos = nx.spring_layout(G)
  print pos
  
  host_addr = {}
  host_addr_list = []
  
  for key, value in pos.iteritems():
    host_addr_list.append(get_ip_addr2(key))

    if key == hostname:
      colors.append('r')
    else:
      colors.append('#8fc5ff')

  print host_addr_list
  
  
  fig, ax = plt.subplots(subplot_kw=dict(axisbg='#EEEEEE'))
  ax.axis('off')
  ax.xaxis.set_major_formatter(plt.NullFormatter())
  ax.yaxis.set_major_formatter(plt.NullFormatter())

  scatter = nx.draw_networkx_nodes(G, pos, node_size=2000, node_color=colors, ax=ax)
  line = nx.draw_networkx_edges(G, pos, width=7, ax=ax)
  
  label_pos = {}
  for key, value in pos.iteritems():
    label_x = value[0]
    label_y = value[1] #- 0.075

    label_pos[key] = np.array([label_x, label_y])


  
  nx.draw_networkx_labels(G, label_pos ,font_size=16, font_color="#000000", ax=ax)
  

  plt.xticks([])
  plt.yticks([])

  plt.axis('off')
  #labels = G.nodes()

  print 'pospospos'
  print pos
  labels = []
  for key, value in pos.iteritems():
    if key == hostname:
      print key + "-" + hostname
      continue 

    table = '<table class="table">'
    table += '<tr class="warning"><th colspan="2">Interface</th><tr>'
    table += '<tr class="warning"><th>' + hostname + '</th><th>' + key + '</th></tr>'
    print key
    for array in port_dict[key]:
      table += '<tr class="warning"><td>' + array[0] + '</td><td>' + array[1] + '</td></tr>'
    table += "</table>"
    labels.append(table)

  #table = '''
  #<table class="table table-condensed">
  #<tr class="warning"><th colspan="2">Interface</th></tr>
  #<tr class="warning"><td>SW1</td><td>SW2</td></tr>
  #<tr class="warning"><td>ge-0/0/0</td><td>ge-0/0/1</td></tr>
  #</table>
  #'''
  #labels=[]
  #for i in neighbors:
  #  labels.append(table)

  tooltip = plugins.PointHTMLTooltip(line, labels=labels)
  #tooltip = plugins.PointHTMLTooltip(line, labels=labels, css=css)

  mpld3.plugins.connect(fig, tooltip)
  mpld3.plugins.connect(fig, ClickInfo(scatter, host_addr_list))
  
  
  mpld3.save_html(fig, config.PYEZ_DEV_INFO_DIR + 'fig/' + ip_addr, d3_url='./static/d3.v3.min.js', mpld3_url='./static/mpld3.v0.2.js')



