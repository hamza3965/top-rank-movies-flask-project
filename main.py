from flask import Flask, render_template, redirect, url_for, flash
from flask_bootstrap import Bootstrap5
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, String, Float, desc
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, FloatField
from wtforms.validators import DataRequired
from dotenv import load_dotenv
from sqlalchemy.exc import IntegrityError
import logging
import os
import requests

MOVIE_DB_SEARCH_URL = "https://api.themoviedb.org/3/search/movie?include_adult=false&language=en-US&page=1/"
MOVIE_DB_INFO_URL = "https://api.themoviedb.org/3/movie"
MOVIE_DB_IMAGE_URL = "https://image.tmdb.org/t/p/w300/"
MOVIE_DB_API_KEY = os.getenv("API_KEY")

load_dotenv()

class RateMovieForm(FlaskForm):
    rating = FloatField(label='Your Rating Out of 10 e.g. 7.5', validators=[DataRequired()])
    review = StringField(label='Your Review', validators=[DataRequired()])
    submit = SubmitField(label="Done")

class AddMovieTitle(FlaskForm):
    title = StringField(label='Movie Title', validators=[DataRequired()])
    submit = SubmitField(label="Add Movie")

app = Flask(__name__)
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'
Bootstrap5(app)

# CREATE DB
class Base(DeclarativeBase):
    pass
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///movies.db'
db = SQLAlchemy(model_class=Base)
db.init_app(app)

# CREATE TABLE
class Movie(db.Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(250), unique=True, nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    rating: Mapped[float] = mapped_column(Float, nullable=True)
    ranking: Mapped[int] = mapped_column(Integer, nullable=True)
    review: Mapped[str] = mapped_column(String(250), nullable=True)
    img_url: Mapped[str] = mapped_column(String(250), nullable=False)

with app.app_context():
    db.create_all()

@app.route("/")
def home():
    result = db.session.execute(db.select(Movie).order_by(Movie.rating))
    all_movies = result.scalars().all()
    for i in range(len(all_movies)):
        all_movies[i].ranking = len(all_movies) - i

    db.session.commit()
    return render_template("index.html", movies=all_movies)

@app.route("/edit/<int:movie_id>", methods=["GET", "POST"])
def rate_movie(movie_id):
    form = RateMovieForm()
    movie = db.get_or_404(Movie, movie_id)

    if movie.rating is not None:
        form.rating.render_kw = {"placeholder": movie.rating}

    if movie.review:
        form.review.render_kw = {"placeholder": movie.review}

    if form.validate_on_submit():
        movie.rating = form.rating.data
        movie.review = form.review.data
        db.session.commit()
        return redirect(url_for("home"))
    return render_template("edit.html", form=form, movie=movie)

@app.route("/delete/<int:movie_id>")
def delete_movie(movie_id):
    movie = db.get_or_404(Movie, movie_id)
    db.session.delete(movie)
    db.session.commit()
    return redirect(url_for("home"))

@app.route("/add", methods=["GET", "POST"])
def add_movie():
    form = AddMovieTitle()
    if form.validate_on_submit():
        movie_title = form.title.data
        response = requests.get(MOVIE_DB_SEARCH_URL, params={"api_key": MOVIE_DB_API_KEY, "query": movie_title})
        data = response.json()["results"]
        return render_template("select.html", options=data)
    return render_template("add.html", form=form)

@app.route("/find/<int:movie_id>")
def find_movie(movie_id):
    if movie_id:
        movie_api_url = f"{MOVIE_DB_INFO_URL}/{movie_id}"
        response = requests.get(movie_api_url, params={"api_key": MOVIE_DB_API_KEY, "language": "en-US"})
        data = response.json()
        try:
            new_movie = Movie(
                title=data["original_title"],
                year=data["release_date"].split("-")[0],
                img_url=f"{MOVIE_DB_IMAGE_URL}{data['poster_path']}",
                description=data["overview"]
            )
            db.session.add(new_movie)
            db.session.commit()
        except IntegrityError as e:
            logging.error(f"IntegrityError occurred: {e}")
            db.session.rollback()
            flash("A movie with this title already exists. Please choose a different title.", "error")
            return redirect(url_for("home"))
        return redirect(url_for("rate_movie", movie_id=new_movie.id))

if __name__ == '__main__':
    app.run(debug=True)
