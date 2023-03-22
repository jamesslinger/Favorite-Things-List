from flask import Flask, render_template, redirect, url_for, request, flash
from flask_bootstrap import Bootstrap
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, DecimalRangeField, TextAreaField
import requests as rq
from datetime import datetime
import os


TMDB_API_KEY = os.environ.get("TMDB_API_KEY")
TMDB_ENDPOINT = "https://api.themoviedb.org/3/search/movie"

YT_API_KEY = os.environ.get("YT_API_KEY")
YT_ENDPOINT = "https://www.googleapis.com/youtube/v3/search"

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get("SECRET_KEY")
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("SQLALCHEMY_DATABASE_URI")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
Bootstrap(app)
db = SQLAlchemy(app)

CURRENT_YEAR = datetime.now().year


##################################### SONGS DB #####################################
class Songs(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    rating = db.Column(db.Float, server_default='Add your rating!')
    rank = db.Column(db.Integer)
    song_url = db.Column(db.Text, nullable=False)
    img_url = db.Column(db.Text, nullable=False)
    date_added = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self):
        return '<Song: %r>' % self.title


##################################### MOVIES DB #####################################
class Movies(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    year = db.Column(db.Integer)
    description = db.Column(db.String(200), nullable=False)
    rating = db.Column(db.Float, server_default='Add your rating!')
    rank = db.Column(db.Integer)
    review = db.Column(db.Text, server_default='Add your review!')
    img_url = db.Column(db.Text, nullable=False)
    imdb_link = db.Column(db.Text, nullable=False)
    date_added = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self):
        return '<Movie: %r>' % self.title


##################################### SONGS FORMS #####################################
class SearchForSong(FlaskForm):
    keyword = StringField(label="SEARCH BY ARTIST OR TRACK NAME")
    submit = SubmitField(label="SEARCH")


class AddSong(FlaskForm):
    title = StringField(label="SONG TITLE")
    artist = StringField(label="ARTIST")
    rating = DecimalRangeField(label="RATING")
    img_url = StringField(label="IMAGE URL")
    submit = SubmitField(label="ADD SONG")


class UpdateSong(FlaskForm):
    rating = DecimalRangeField(label="RATING")
    submit = SubmitField(label="UPDATE")


##################################### MOVIES FORMS #####################################
class SearchForMovie(FlaskForm):
    title = StringField(label="SEARCH BY TITLE")
    submit = SubmitField(label="SEARCH")


class AddMovie(FlaskForm):
    title = StringField(label="Title: ")
    year = StringField(label="Year: ")
    description = StringField(label="Description: ")
    rating = DecimalRangeField(label="Rating: ")
    rank = StringField(label="Rank: ")
    review = StringField(label="Review: ")
    img_url = StringField(label="Image URL: ")
    submit = SubmitField(label="ADD MOVIE")


class EditRating(FlaskForm):
    rating = DecimalRangeField(label="RATING")
    review = TextAreaField(label="REVIEW")
    submit = SubmitField(label="UPDATE")


##################################### MAIN MENU #####################################
@app.route("/")
def menu():
    return render_template("menu.html", year=CURRENT_YEAR)


##################################### SONGS FUNCTIONS #####################################
@app.route("/songs")
def songs():
    db.create_all()
    empty_check = db.session.query(Songs).first()
    if empty_check is None:
        return render_template("songs.html", nav_title="My Top Songs", sec_desc="List empty! Please add a song.", year=CURRENT_YEAR)
    all_songs = Songs.query.order_by(Songs.rating).all()
    for i in range(len(all_songs)):
        all_songs[i].rank = len(all_songs) - i
    db.session.commit()
    return render_template("songs.html", all_songs=all_songs, nav_title="My Top Songs", sec_desc="My favourite tunes from the past 20 years.", year=CURRENT_YEAR)


@app.route("/songs/search", methods=["GET", "POST"])
def song_search():
    form = SearchForSong()
    if form.validate_on_submit():
        try:
            yt_params = {
            "key": YT_API_KEY,
            "q": form.keyword.data,
            "type": "video",
            "part": "snippet",
            "maxResults": "24",
            }
            response = rq.get(url=YT_ENDPOINT, params=yt_params)
            response.raise_for_status()
            search_data = response.json()['items']
            return render_template("select_song.html", songs=search_data, form=AddSong(), year=CURRENT_YEAR)
        except:
            return render_template("song_search.html", form=form, year=CURRENT_YEAR)
    return render_template("song_search.html", form=form, year=CURRENT_YEAR)


@app.route("/songs/add-selected-song", methods=["GET", "POST"])
def add_selected_song():
    if request.method == "POST":
        song_id = request.form['id']
        song_url = f"https://www.youtube.com/watch?v={song_id}"
        yt_params = {
            "key": YT_API_KEY,
            "id": song_id,
            "part": "snippet"
        }
        response = rq.get(url="https://www.googleapis.com/youtube/v3/videos", params=yt_params)
        response.raise_for_status()
        song_data = response.json()['items'][0]['snippet']
        new_song = Songs(title = song_data['title'],
                         year = song_data['publishedAt'].split('-')[0],
                         song_url = song_url,
                         img_url = song_data['thumbnails']['high']['url'])
        db.session.add(new_song)
        db.session.commit()
        flash(f'New Song: "{song_data["title"]}" added!')
        song_title = song_data['title']
        return redirect(url_for('rate_song', title=song_title))
    return render_template(url_for('add_selected_song', year=CURRENT_YEAR))


@app.route("/songs/rating", methods=["GET", "POST"])
def rate_song():
    form = UpdateSong()
    if form.validate_on_submit():
        song_to_rate = Songs.query.filter_by(title=request.form['title']).first()
        song_to_rate.rating = request.form['rating']
        db.session.commit()
        return redirect(url_for('songs'))
    song_id = request.args.get('id')
    song_title = request.args.get('title')
    current_rating = request.args.get('rating')
    return render_template('rate_song.html', form=form, title=song_title, id=song_id, rating=current_rating, year=CURRENT_YEAR)


@app.route("/songs/update", methods=["GET", "POST"])
def update_song():
    form = UpdateSong()
    if form.validate_on_submit():
        song_to_update = Songs.query.filter_by(title=request.form['title']).first()
        song_to_update.rating = request.form['rating']
        db.session.commit()
        flash(f'"{request.form["title"]}" updated!')
        return redirect(url_for('songs'))
    song_title = request.args.get('title')
    current_rating = request.args.get('rating')
    return render_template('update_song.html', form=form, title=song_title, rating=current_rating, year=CURRENT_YEAR)


@app.route("/songs/delete", methods=["GET", "POST"])
def delete_song():
    song_id = request.args.get('id')
    song_to_delete = Songs.query.get(song_id)
    db.session.delete(song_to_delete)
    db.session.commit()
    flash(f'"{request.args.get("title")}" deleted!')
    return redirect((url_for('songs')))


##################################### MOVIES FUNCTIONS #####################################
@app.route("/movies")
def movies():
    db.create_all()
    empty_check = db.session.query(Movies).first()
    if empty_check is None:
        return render_template('movies.html', nav_title="My Top Movies" ,sec_desc="List empty! Please add a movie.", year=CURRENT_YEAR)
    all_movies = Movies.query.order_by(Movies.rating).all()
    for i in range(len(all_movies)):
        all_movies[i].rank = len(all_movies) - i
    db.session.commit()
    return render_template("movies.html", all_movies=all_movies, nav_title="My Top Movies", sec_desc="These are my all time favourite movies.", year=CURRENT_YEAR)


@app.route("/movies/movie-search", methods=["GET", "POST"])
def movie_search():
    form = SearchForMovie()
    if form.validate_on_submit():
        try:
            tmdb_params = {
                "api_key": TMDB_API_KEY,
                "query": form.title.data,
            }
            response = rq.get(url=TMDB_ENDPOINT, params=tmdb_params)
            response.raise_for_status()
            search_data = response.json()['results']
            return render_template('select_movie.html', titles=search_data, form=AddMovie(), year=CURRENT_YEAR)
        except:
            return render_template("movie_search.html", form=form, year=CURRENT_YEAR)
    return render_template("movie_search.html", form=form, year=CURRENT_YEAR)


@app.route("/movies/add-selected-movie", methods=["GET", "POST"])
def add_selected_movie():
    if request.method == "POST":
        movie_id = request.form['id']
        tmdb_params = {
            "api_key": TMDB_API_KEY,
        }
        movie_url = f"https://api.themoviedb.org/3/movie/{movie_id}"
        response = rq.get(url=movie_url, params=tmdb_params)
        response.raise_for_status()
        movie_to_add = response.json()
        new_movie = Movies(title = movie_to_add['original_title'],
                          year = movie_to_add['release_date'].split('-')[0],
                          description = movie_to_add['overview'],
                          img_url = f"https://image.tmdb.org/t/p/original{movie_to_add['poster_path']}",
                          imdb_link = f"https://www.imdb.com/title/{movie_to_add['imdb_id']}")
        db.session.add(new_movie)
        db.session.commit()
        flash(f'New Movie: "{movie_to_add["original_title"]}" added!')
        movie_title = movie_to_add['original_title']
        return redirect(url_for('rate_movie', movie_title=movie_title))
    return render_template(url_for('add_selected_movie', year=CURRENT_YEAR))


@app.route('/movies/rate-review', methods=['GET', 'POST'])
def rate_movie():
    form = EditRating()
    if form.validate_on_submit():
        movie_to_edit = Movies.query.filter_by(title=request.form['title']).first()
        movie_to_edit.rating = request.form['rating']
        movie_to_edit.review = request.form['review']
        db.session.commit()
        return redirect(url_for('movies'))
    movie_title = request.args['movie_title']
    return render_template('rate_movie.html', form=form, title=movie_title, year=CURRENT_YEAR)


@app.route('/movies/update', methods=["GET", "POST"])
def update_movie():
    form = EditRating()
    if form.validate_on_submit():
        movie_to_update = Movies.query.filter_by(title=request.form['title']).first()
        movie_to_update.rating = request.form['rating']
        movie_to_update.review = request.form['review']
        db.session.commit()
        flash(f'"{request.form["title"]}" updated!')
        return redirect(url_for('movies'))
    movie_title = request.args.get('title')
    current_rating = request.args.get('rating')
    current_review = request.args.get('review')
    return render_template('update_movie.html', form=form, title=movie_title, rating=current_rating, review=current_review, year=CURRENT_YEAR)


@app.route('/movies/delete')
def delete_movie():
    movie_id = request.args.get('id')
    movie_to_delete = Movies.query.get(movie_id)
    db.session.delete(movie_to_delete)
    db.session.commit()
    flash(f'"{request.args.get("title")}" deleted!')
    return redirect(url_for('movies'))


if __name__ == '__main__':
    app.run()
