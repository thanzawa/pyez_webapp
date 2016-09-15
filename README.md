## Web application used PyEZ + Flask
====


## Overview
Juniper PyEZを用いたWebアプリケーションを実装しています。

指定したアドレス範囲内でJunosデバイスを探索し、複数台のデバイスに対する設定の変更や情報の取得を行います。


## Features
* デバイスとの接続と情報の取得
* 任意のデバイスの情報の表示
* 設定情報の一括変更
* 取得情報を基にしたトポロジの可視化
* （今後、その他の機能を追加予定）


* Connect to Junos devices and collect device informations
* Show device informations at selected devices
* Change configurations at selected devices
* Visualization of network topology using PyEZ, NetworkX, Matplotlib, mpld3
* (Under Development)

## Requirements

* Server

  Installing Python 2.6 or 2.7, and Junos PyEZ.

  In detail, please refer to URL below.

  <http://www.juniper.net/techpubs/en_US/junos-pyez1.0/topics/task/installation/junos-pyez-server-installing.html>

* Junos Devices

  Enable NETCONF and lldp

  `set system services netconf ssh`

  `set system services lldp interface all`

## Install

* Install libraries

  `pip install -r requirements.txt`


* Run

  `python app.py`



