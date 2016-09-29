#i coding: utf-8
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
import pydotplus
from numpy import array
import mpld3
from mpld3 import utils, plugins
import sys,os
import config
import time
import traceback
import shutil
from bs4 import BeautifulSoup
import warnings;warnings.filterwarnings('ignore')

Device.auto_probe = 1 

def call_dev(ip_addr, user, password):
  dev = Device(host=ip_addr, user=user, password=password)
  return dev

def host_to_addr(ip_addr, user, password):

  dev = call_dev(ip_addr, user, password)
  
  try:
    dev.open()
  except:
    print ip_addr + "- not connected"
    delete_info_files(ip_addr)
    return

  delete_info_files(ip_addr)
  dev_dict = dev.facts
  filename = config.PYEZ_FLASK_DIR + 'host_addr.txt'
  f = open(filename, 'a')
  f.write(str(dev_dict.get('hostname')) + ',' + ip_addr + '\n')
  f.close()
  dev.close()


def get_device_information2(ip_addr, user, password):
  dev = call_dev(ip_addr, user, password)
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

    if os.path.isfile(config.PYEZ_DEV_INFO_DIR + 'fig/' + ip_addr):
      os.remove(config.PYEZ_DEV_INFO_DIR + 'fig/' + ip_addr)

    if os.path.isfile(config.PYEZ_DEV_INFO_DIR + 'hardware/' + ip_addr):
      os.remove(config.PYEZ_DEV_INFO_DIR + 'hardware/' + ip_addr)
    return None
  
  dev_dict = dev.facts


  result = ''
  result += '<th><a href="./' + ip_addr + '">' + ip_addr + '</a></th>'
  result += '<th id="host">' + str(dev_dict.get('hostname')) + '</th>'
  result += '<th>' + str(dev_dict.get('model')) + '</th>'
  result += '<th>' + str(dev_dict.get('version')) + '</th>'

  filename = config.PYEZ_DEV_INFO_DIR + 'facts/' + ip_addr 
  f = open(filename, 'w')
  f.write(result)
  f.close()


  lldp_result = create_lldp_table(dev, ip_addr, str(dev_dict.get('hostname')))
  create_vlan_table(dev, ip_addr)
  create_hardware_table(dev, ip_addr)
  
  if lldp_result[0] != []:
    if os.path.isfile(config.PYEZ_DEV_INFO_DIR + 'fig/' + ip_addr):
      os.remove(config.PYEZ_DEV_INFO_DIR + 'fig/' + ip_addr)
    create_neighbors_fig_mpld3(dev_dict.get('hostname'), lldp_result[0], ip_addr, lldp_result[1])
  elif lldp_result[0] == [] and os.path.isfile(config.PYEZ_DEV_INFO_DIR + 'fig/' + ip_addr):
    os.remove(config.PYEZ_DEV_INFO_DIR + 'fig/' + ip_addr)
  
  dev.close()
  


def get_device_information(ip_addr):
  dev = call_dev(ip_addr, user, password)
   
  try:
    dev.open()

  except:
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


def create_hardware_table(dev, ip_addr):
  result = '<table class="table table-striped">\n<tr>\n<th>Item</th>\n<th>Version</th>\n<th>Part number</th>\n<th>Serial number</th>\n<th>Description</th>\n</tr>\n'

  try:
    rpc_response = etree.tostring(dev.rpc.get_chassis_inventory())
  except:
    return
  
  root = etree.fromstring(rpc_response)
  entries = root.xpath('//chassis')

  for entry in entries:
    hard = {}

    if entry.find('name') is not None:
      hard['name'] = str(entry.find('name').text)
    else:
      hard['name'] = ""
    if entry.find('version') is not None:
      hard['version'] = str(entry.find('version').text)
    else:
      hard['version'] = ""
    if entry.find('part-number') is not None:
      hard['part-number'] = str(entry.find('part-number').text)
    else:
      hard['part-number'] = ""
    if entry.find('serial-number') is not None:
      hard['serial-number'] = str(entry.find('serial-number').text)
    else:
      hard['serial-number'] = ""
    if entry.find('description') is not None:
      hard['description'] = str(entry.find('description').text)
    else:
      hard['description'] = ""
  
    result += '<tr>\n<td>' + hard["name"] + '</td>\n'
    result += '<td></td>\n'
    result += '<td></td>\n'
    result += '<td>' + hard["serial-number"] + '</td>\n' 
    result += '<td>' + hard["description"] + '</td>\n</tr>\n'

  entries = root.xpath('//chassis-module')
  
  for entry in entries:
    hard = {}
    if entry.find('name') is not None:
      hard['name'] = str(entry.find('name').text)
    else:
      hard['name'] = ""
    if entry.find('version') is not None:
      hard['version'] = str(entry.find('version').text)
    else:
      hard['version'] = ""
    if entry.find('part-number') is not None:
      hard['part-number'] = str(entry.find('part-number').text)
    else:
      hard['part-number'] = ""
    if entry.find('serial-number') is not None:
      hard['serial-number'] = str(entry.find('serial-number').text)
    else:
      hard['serial-number'] = ""
    if entry.find('description') is not None:
      hard['description'] = str(entry.find('description').text)
    else:
      hard['description'] = ""
  
    result += '<tr>\n<td>' + hard["name"] + '</td>\n'
    result += '<td>' + hard["version"] + '</td>\n'
    result += '<td>' + hard["part-number"] + '</td>\n'
    result += '<td>' + hard["serial-number"] + '</td>\n' 
    result += '<td>' + hard["description"] + '</td>\n</tr>\n'
    
    if entry.find('chassis-sub-module') is not None:
      sub_entry = entry.xpath('//chassis-sub-module')
      
      for entry in sub_entry:
        hard = {}
        if entry.find('name') is not None:
          hard['name'] = str(entry.find('name').text)
        else:
          hard['name'] = ""
         
        if entry.find('version') is not None:
          hard['version'] = str(entry.find('version').text)
        else:
          hard['version'] = ""

        if entry.find('part-number') is not None:
          hard['part-number'] = str(entry.find('part-number').text)
        else:
          hard['part-number'] = ""
         
        if entry.find('serial-number') is not None:
          hard['serial-number'] = str(entry.find('serial-number').text)
        else:
          hard['serial-number'] = ""
        
        if entry.find('description') is not None:
          hard['description'] = str(entry.find('description').text)
        else:
          hard['description'] = ""
      
        result += '<tr>\n<td>' + hard["name"] + '</td>\n'
        result += '<td>' + hard["version"] + '</td>\n'
        result += '<td>' + hard["part-number"] + '</td>\n'
        result += '<td>' + hard["serial-number"] + '</td>\n' 
        result += '<td>' + hard["description"] + '</td>\n</tr>\n'
      
  result += '</table>'

  f = open(config.PYEZ_DEV_INFO_DIR + 'hardware/' + ip_addr, 'w')
  f.write(result)
  f.close()


def create_lldp_table(dev, ip_addr, hostname):
  result = '<table class="table table-striped">\n<tr>\n<th>Local Interface</th>\n<th>Remote Hostname</th>\n<th>Remote Interfaces</th>\n</tr>\n'
 
  neighbors = []
  port_dict = {}

  try:
    rpc_response = etree.tostring(dev.rpc.get_lldp_neighbors_information())
  
    root = etree.fromstring(rpc_response)
    entries = root.xpath('//lldp-neighbor-information')
    
    
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
      elif entry.find('lldp-remote-chassis-id') is not None and entry.find('lldp-remote-chassis-id-subtype') is not None and entry.find('lldp-remote-chassis-id-subtype').text == 'Mac address':
        lldp_dict["remote_host"] = entry.find('lldp-remote-chassis-id').text
      else:
        lldp_dict["remote_port"] = ""
      
      result += '<tr class="' + lldp_dict["remote_host"] + '">\n<td class="local_i">' + lldp_dict["local_i"] + '</td>\n'
      result += str(get_ip_addr(lldp_dict.get('remote_host')))
      result += '<td class="remote_port">' + lldp_dict["remote_port"] + '</td>\n</tr>\n'
   
     
      if port_dict.get(str(lldp_dict.get("remote_host"))) is None:
        port_dict[str(lldp_dict.get("remote_host"))] = [[lldp_dict.get("local_i"), lldp_dict.get("remote_port")]]
      else:
        port_dict[str(lldp_dict.get("remote_host"))].append([lldp_dict.get("local_i"), lldp_dict.get("remote_port")])
      

    if len(entries) == 0:
      result += '<tr>\n<td colspan="3">None</td>\n</tr>'


    result += '</table>\n'
  
  except EzErrors.RpcError:
    result += '<tr>\n<td colspan="3">lldp service is not runnning</td>\n</tr>\n</table>'
    if os.path.isfile(config.PYEZ_DEV_INFO_DIR + 'fig/' + ip_addr):
      os.remove(config.PYEZ_DEV_INFO_DIR + 'fig/' + ip_addr)
  except EzErrors.ConnectClosedError:
    result += '<tr>\n<td colspan="3">Connection unexpectedly closed</td>\n</tr>\n</table>'
    
    if os.path.isfile(config.PYEZ_DEV_INFO_DIR + 'fig/' + ip_addr):
      os.remove(config.PYEZ_DEV_INFO_DIR + 'fig/' + ip_addr)

  f = open(config.PYEZ_DEV_INFO_DIR + 'lldp/' + ip_addr, 'w')
  f.write(result)
  f.close()

  return [neighbors, port_dict]



def get_neighbors_fig(ip_addr):
  if os.path.isfile(config.PYEZ_FLASK_DIR + 'static/' + ip_addr + '.png') == True:

    return [ip_addr + '.png']
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
  
  pos = nx.spring_layout(G)
   
  nx.draw_networkx_nodes(G, pos, node_size=500, node_color=colors)
  nx.draw_networkx_edges(G, pos, width=1)
  nx.draw_networkx_labels(G, pos ,font_size=16, font_color="#000000")
  
  plt.xticks([])
  plt.yticks([])
  plt.savefig(config.PYEZ_FLASK_DIR + 'static/' + ip_addr + '.png')


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
  result = '<td class="neighbors">'
  
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
     
  node_list1 = [hostname]
  node_list2 = neighbors[:]
  nodes = neighbors[:]
  nodes.append(hostname)
  children = neighbors
  g_children = []


  for neighbor in neighbors:
    result =  get_neighbors_list(neighbor, hostname)
    
    for n in result:
      nodes.append(n)
      g_children.append(n)
      port_list = get_port_num_list(n, neighbor)
      port_dict[n] = port_list
      port_dict['basehost_' + n] = neighbor

  
  G = nx.Graph()
  G.add_nodes_from(nodes)
  colors = []
  added_nodes = []
 

  for neighbor in neighbors:
    G.add_edge(hostname, neighbor)
    added_nodes.append(neighbor)
    

  for neighbor in neighbors:
    result =  get_neighbors_list(neighbor, hostname)

    for sub_neighbor in result:
        G.add_edge(neighbor, sub_neighbor)


  pos = hierarchy_pos(G, hostname, list(set(children)), list(set(g_children)))
  host_addr = {}
  host_addr_list = []
  
  for node in G.nodes():

    host_addr_list.append(get_ip_addr2(node))
    
    if node == hostname:
      colors.append('r')
    else:
      colors.append('#8fc5ff')

  fig, ax = plt.subplots(subplot_kw=dict(axisbg='#EEEEEE'))
  ax.axis('off')
  ax.xaxis.set_major_formatter(plt.NullFormatter())
  ax.yaxis.set_major_formatter(plt.NullFormatter())

  scatter = nx.draw_networkx_nodes(G, pos=pos, node_size=3000, node_shape='s', node_color=colors, ax=ax)
  line = nx.draw_networkx_edges(G, pos=pos, width=7, ax=ax)
  
  nx.draw_networkx_labels(G, pos=pos ,font_size=16, font_color="#000000", ax=ax)

  plt.xticks([])
  plt.yticks([])

  plt.axis('off')

  labels = []
  
  
  for key in G.edges():
    
    table = '<table class="table table-bordered">'
    table += '<tr class="active"><th>' + key[0] + '</th><th>' + key[1] + '</th></tr>'
   
    result = get_port_pair([key[1], key[0]])
    #result = get_port_pair([key[0], key[1]])
    
    for port in result:
      table += '<tr class="active"><td>' + str(port[0]) + '</td><td>' + str(port[1]) + '</td></tr>'
    
    table += "</table>"
    labels.append(table)

  tooltip = plugins.PointHTMLTooltip(line, labels=labels)

  mpld3.plugins.connect(fig, tooltip)
  mpld3.plugins.connect(fig, ClickInfo(scatter, host_addr_list))
  
  mpld3.save_html(fig, config.PYEZ_DEV_INFO_DIR + 'fig/' + ip_addr, d3_url='./static/d3.v3.min.js', mpld3_url='./static/mpld3.v0.2.js')



def get_neighbors_list(hostname, base_host):
  f = open(config.PYEZ_FLASK_DIR + 'host_addr.txt')
  addr_list = f.read().rstrip().split('\n')
  host_addr = ""

  for addr in addr_list:
    if addr.split(',')[0] == hostname:
      host_addr = addr.split(',')[1]
  if host_addr == "":
    return []
  
  
  try:
    f = open(config.PYEZ_DEV_INFO_DIR + 'lldp/' + host_addr)
    html = f.read()
    soup = BeautifulSoup(html, "lxml")
    neighbors_list = [tag.text for tag in soup.find_all("td", class_="neighbors")]
    neighbors_list.remove(base_host)
    return neighbors_list

  except:
    return []

def get_port_pair(array):
  
  f = open(config.PYEZ_FLASK_DIR + 'host_addr.txt')
  addr_list = f.read().rstrip().split('\n')
  left_addr = ""
  right_addr = ""

  for addr in addr_list:
    if addr.split(',')[0] == array[1]:
      left_addr = addr.split(',')[1]
      break

    if addr.split(',')[0] == array[0]:
      right_addr = addr.split(',')[1]
      break


  if left_addr != "": 
    try:
      f = open(config.PYEZ_DEV_INFO_DIR + 'lldp/' + left_addr)
      html = f.read()
      soup = BeautifulSoup(html, "lxml")
      list1 = soup.find_all("tr", class_ = array[0])
      result = []
      
      for i in list1:
        result.append([i.find('td', class_="local_i").text, i.find('td', class_="remote_port").text])
      
      return result
  
    except:
      return [['-', '-']]
  elif right_addr != "":
    try:
      f = open(config.PYEZ_DEV_INFO_DIR + 'lldp/' + right_addr)
      html = f.read()
      soup = BeautifulSoup(html, "lxml")
      list1 = soup.find_all("tr", class_ = array[1])
      result = []
      
      for i in list1:
        result.append([i.find('td', class_="remote_port").text, i.find('td', class_="local_i").text])
      
      return result
  
    except:
      return [['-', '-']]
   
  else:
    return [['-', '-']]

def get_port_num_list(remote_host, base_host):
  
  f = open(config.PYEZ_FLASK_DIR + 'host_addr.txt')
  addr_list = f.read().rstrip().split('\n')
  host_addr = ""

  for addr in addr_list:
    if addr.split(',')[0] == base_host:
      base_addr = addr.split(',')[1]
      break

  try:
    f = open(config.PYEZ_DEV_INFO_DIR + 'lldp/' + base_addr)
    html = f.read()
    soup = BeautifulSoup(html, "lxml")
    list1 = soup.find_all("tr", class_ = remote_host)
    result = []
    for i in list1:
      result.append([i.find('td', class_="local_i").text, i.find('td', class_="remote_port").text])
    
    return result
  except:
    return [['-', '-']]
    

def delete_info_files(ip_addr):
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




def hierarchy_pos(G, hostname, children, g_children, width=0.9, vert_gap = 0.2, vert_loc = 0, xcenter = 0.5):
  
  pos = {} 
  pos[hostname] = (xcenter, vert_loc)
  
  if len(children) != 0:
    dx = width / len(children)
    nextx = xcenter - width / 2 - dx / 2 
    vert_loc = vert_loc - vert_gap
    
    for child in children:
      nextx += dx
      pos[child] = (nextx, vert_loc)
 
  if len(g_children) != 0:
    dx = width / len(g_children) 
    nextx = xcenter - width / 2 - dx / 2
    vert_loc = vert_loc - vert_gap
   
    for g_child in g_children:
      nextx += dx
      pos[g_child] = (nextx, vert_loc)

  return pos



