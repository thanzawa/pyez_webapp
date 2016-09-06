# pyez_webapp
====

## Overview
Juniper PyEZを用いたWebアプリケーションを実装しています。

指定したアドレス範囲内でJunosデバイスを探索し、複数台のデバイスに対する設定の変更や情報の取得を行います。


## Features
* デバイスとの接続と情報の取得
* 任意のデバイスの情報の表示
* 取得情報を基にしたトポロジの可視化など
* （今後、機能を追加予定）

## Install

`pip install -r requirements.txt`

で必要なライブラリ等をインストールし

`python app.py`

でサーバを起動

デフォルトではユーザ名、パスワードはそれぞれuser, passwordとなっています。

pyez_flask/config.txtで環境に合わせて変更してください。

