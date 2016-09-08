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
* Visualization of network topology
* (Under Development)

## Install

`pip install -r requirements.txt`

で必要なライブラリ等をインストールし

`python app.py`

でサーバを起動



