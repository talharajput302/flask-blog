from flask import Flask, render_template, request, session, flash
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail
import json
import os
from datetime import datetime
from flask import redirect
from werkzeug.utils import secure_filename
import math


with open('config.json', 'r') as c:
    params = json.load(c)['params']

local_server = os.environ.get('LOCAL_SERVER') == 'True'

app = Flask(__name__)
app.secret_key = 'super-secret-key'
app.config['UPLOAD_FOLDER'] = params['upload_location']
app.config.update(
    MAIL_SERVER = 'smtp.gmail.com',
    MAIL_PORT = 465,
    MAIL_USE_SSL = True,
    MAIL_USERNAME = params['gmail-user'],
    MAIL_PASSWORD = params['gmail-password'],
)
mail = Mail(app)
if local_server:
    app.config['SQLALCHEMY_DATABASE_URI'] = params['local_uri']
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = params['prod_uri']
db = SQLAlchemy(app)

class Contact(db.Model):
    sno = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(20), nullable=False)
    phone_num = db.Column(db.String(12), nullable=False)
    msg = db.Column(db.String(120), nullable=False)
    date = db.Column(db.String(20), nullable=True)

class Posts(db.Model):
    sno = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(80), nullable=False)
    slug = db.Column(db.String(21), nullable=False)
    content = db.Column(db.String(120), nullable=False)
    date = db.Column(db.String(20), nullable=True)
    img_file = db.Column(db.String(12), nullable=True)


@app.route('/')
def home():
    posts = Posts.query.filter_by().all()
    last = math.ceil(len(posts)/int(params['num_of_posts']))
    page = request.args.get('page')
    if not str(page).isnumeric():
        page = 1
    page = int(page)
    posts = posts[(page-1)*int(params['num_of_posts']):(page-1)*int(params['num_of_posts'])+int(params['num_of_posts'])]
    if page == 1:
        prev = "#"
        next_page = "/?page="+str(page+1)
    elif page == last:
         prev = "/?page=" + str(page-1)
         next_page = "#"
    else:
        prev = "/?page="+str(page-1)
        next_page = "/?page="+str(page+1)

    return render_template('index.html', params = params, posts=posts, prev=prev, next=next_page)

@app.route('/post/<string:post_slug>', methods=['GET'])
def post_route(post_slug):
    post = Posts.query.filter_by(slug=post_slug).first()
    return render_template('post.html', params = params, post=post)

@app.route('/about')
def about():
    return render_template('about.html', params = params)

@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    # First: Check if already logged in
    if "user" in session and session["user"] == params["admin_user"]:
        posts = Posts.query.all()
        return render_template("dashboard.html", params=params, posts=posts)

    # Second: Handle login attempt
    if request.method == "POST":
        username = request.form.get("uname")
        userpass = request.form.get("upass")
        if username == params["admin_user"] and userpass == params["admin_password"]:
            session["user"] = username  # Set session
            flash("Welcome Admin!", "success")
            return redirect("/dashboard")



    return render_template("login.html", params=params)


@app.route('/edit/<string:sno>', methods=['GET', 'POST'])
def edit(sno):
    if "user" not in session or session['user'] != params['admin_user']:
        return redirect('/dashboard')

    if request.method == "POST":
        box_title = request.form.get("title")
        slug = request.form.get("slug")
        content = request.form.get("content")
        img_file = request.form.get("img_file")
        date = datetime.now()

        if sno == '0':
            post = Posts(title=box_title, slug=slug, content=content,
                         img_file=img_file, date=date)
            db.session.add(post)
        else:
            post = Posts.query.filter_by(sno=sno).first()
            if post:
                post.title = box_title
                post.slug = slug
                post.content = content
                post.img_file = img_file
                post.date = date

        db.session.commit()
        flash("Successfully updated!", "success")
        return redirect('/dashboard')

    post = None
    if sno != '0':
        post = Posts.query.filter_by(sno=sno).first()
    return render_template("edit.html", params=params, post=post, sno=sno)

@app.route('/uploader', methods=['GET', 'POST'])
def uploader():
    if 'user' in session and session['user'] == params['admin_user']:
        if request.method == "POST":
            f= request.files['file1']
            f.save(os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(f.filename)))
    flash("File successfully uploaded!", "success")
    return redirect('/dashboard')

@app.route('/logout')
def logout():
    session.pop('user')
    return redirect('/dashboard')

@app.route('/delete/<string:sno>', methods=['GET', 'POST'])
def delete(sno):
    if 'user' in session and session['user'] == params['admin_user']:
        post = Posts.query.filter_by(sno=sno).first()
        db.session.delete(post)
        db.session.commit()
    flash("Successfully deleted!", "success")
    return redirect('/dashboard')




@app.route('/contact', methods=['GET', 'POST'])
def contact():

    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        phone_num = request.form['phone_num']
        message = request.form['message']
        entry = Contact(name=name, email=email, date = datetime.now(), phone_num=phone_num, msg=message)
        db.session.add(entry)
        db.session.commit()
        mail.send_message('New Message From ' + name,
                          sender= email,
                          recipients=[params['gmail-user']],
                          body = message + "\n" + phone_num
                          )
        flash("Thanks For Submitting Your Details. We Will Get Back To You Soon!", "success")

    return render_template('contact.html', params = params)


if __name__ == '__main__':
    app.run(debug=True)



