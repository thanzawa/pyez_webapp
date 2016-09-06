from pyez_flask import db

class Entry(db.Model):
  __tablename__ = 'entries'
  id = db.Column(db.Integer, primary_key=True)
  title = db.Column(db.Text)
  text = db.Column(db.Text)


  def __repr__(self):
    return '<Entry id={id} title={title!r}>'.format(id=self.id, title=self.title)

class Dev(db.Model):
  __tablename__ = 'devices'
  id = db.Column(db.Integer, primary_key=True)
  ip_addr = db.Column(db.Text)
  hostname = db.Column(db.Text)
  model = db.Column(db.Text)
  serial_num = db.Column(db.Text)
  os_version = db.Column(db.Text)
  ip_addr_int = db.Column(db.Integer)

  def __repr__(self):
    return '<Dev id={id} ip_addr={ip_addr}>'.format(id=self.id, ip_addr=self.ip_addr)


def init():
  db.create_all()


