# ----------------------------------------------------------------------------#
# Imports
# ----------------------------------------------------------------------------#

import json
import dateutil.parser
import babel
from flask import Flask, render_template, request, Response, flash, redirect, url_for, abort
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
import logging
from logging import Formatter, FileHandler
from pprint import pprint
from flask_wtf import Form, FlaskForm
from forms import *
from jinja2 import BaseLoader, TemplateNotFound, nodes
import datetime
import psycopg2
from flask_migrate import Migrate
import sys
from models import db, Artist, Venue, Show
# ----------------------------------------------------------------------------#
# App Config.
# ----------------------------------------------------------------------------#

app = Flask(__name__)
moment = Moment(app)
app.config.from_object('config')
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# ----------------------------------------------------------------------------#
# Filters.
# ----------------------------------------------------------------------------#

def format_datetime(value, format='medium'):
    date = dateutil.parser.parse(value)
    if format == 'full':
        format = "EEEE MMMM, d, y 'at' h:mma"
    elif format == 'medium':
        format = "EE MM, dd, y h:mma"
    return babel.dates.format_datetime(date, format, locale='en')


app.jinja_env.filters['datetime'] = format_datetime


# ----------------------------------------------------------------------------#
# Controllers.
# ----------------------------------------------------------------------------#

@app.route('/')
def index():
    return render_template('pages/home.html')


#  Venues
#  ----------------------------------------------------------------

@app.route('/venues')
def venues():

    # all states and cities - removing repetitions for similarly named cities and states
    locations = db.session.query(Venue.city, Venue.state).distinct(Venue.city, Venue.state)
    data = []
    # current_time = datetime.now().strftime('%Y-%m-%d %H:%S:%M')

    # looping through to filter individual cities and states
    for location in locations:
        location_result = Venue.query.filter(location.city).filter(location.state).all()
        venue_info = []

        for venue in location_result:
            upcoming_shows = venue.shows.filter(Show.start_time < datetime.now()).all()
            venue_info.append({
                "id": venue.id,
                "name": venue.name,
                "upcoming_shows_count": len(upcoming_shows)
            })

            data.append({
                "city": location.city,
                "state": location.state,
                "venues": venue_info
            })

    return render_template("pages/venues.html", areas=data)


@app.route('/venues/search', methods=['POST'])
def search_venues():
    search_term = request.form.get('search_term', '')
    result = db.session.query(Venue).filter(Venue.name.ilike(f'%{search_term}%')).all()
    count = len(result)
    response = {
        "count": count,
        "data": result
    }
    return render_template('pages/search_venues.html', results=response,
                           search_term=request.form.get('search_term', ''))


@app.route('/venues/<int:venue_id>')
def show_venue(venue_id):
    venue = Venue.query.get(venue_id)
    venue.upcoming_shows = []
    venue.past_shows = []
    venue.past_shows_count = 0
    venue.upcoming_shows_count = 0

    shows = Venue.query.join(Show, Show.venue_id == Venue.id).join(Artist,
            Artist.id == Show.artist_id).add_columns(Show.start_time.label('start_time'),
            Artist.id.label('artist_id'), Artist.name.label('artist_name'),
            Artist.image_link.label('artist_image_link')).filter(Venue.id == venue_id).order_by(Show.start_time.desc()).all()

    for show in shows:
        start = show.start_time
        current = datetime.now()
        if show.start_time < datetime.now():
            venue.past_shows.append(show)
            venue.past_shows_count += 1
        else:
            venue.upcoming_shows.append(show)
            venue.upcoming_shows_count += 1

    return render_template('pages/show_venue.html', venue=venue)


#  Create Venue
#  ----------------------------------------------------------------

@app.route('/venues/create', methods=['GET'])
def create_venue_form():
    form = VenueForm()
    return render_template('forms/new_venue.html', form=form)


@app.route('/venues/create', methods=['POST'])
def create_venue_submission():
    error = False
    try:
        venue = Venue()
        venue.name = request.form['name']
        venue.city = request.form['city']
        venue.state = request.form['state']
        venue.address = request.form['address']
        venue.phone = request.form['phone']
        tmp_genres = request.form.getlist('genres')
        venue.genres = ','.join(tmp_genres)
        venue.facebook_link = request.form['facebook_link']
        db.session.add(venue)
        db.session.commit()
    except:
        error = True
        db.session.rollback()
        print(sys.exc_info())
    finally:
        db.session.close()
        if error:
            flash('An error occured. Venue ' +
                  request.form['name'] + ' Could not be listed!')
        else:
            flash('Venue ' + request.form['name'] +
                  ' was successfully listed!')
    return render_template('pages/home.html')


@app.route('/venues/<venue_id>', methods=['DELETE'])
def delete_venue(venue_id):
    try:
        Venue.query.filter_by(id=venue_id).delete()
        db.session.commit()
    except:
        db.session.rollback()
        print(sys.exc_info())
    finally:
        db.session.close()

    # BONUS CHALLENGE: Implement a button to delete a Venue on a Venue Page, have it so that
    # clicking that button delete it from the db then redirect the user to the homepage
    return None


#  Artists
#  ----------------------------------------------------------------
@app.route('/artists')
def artists():
    response = Artist.query.all()
    return render_template('pages/artists.html', artists=response)


@app.route('/artists/search', methods=['POST'])
def search_artists():
    search_term = request.form.get('search_term', '')
    result = db.session.query(Artist).filter(Artist.name.ilike(f'%{search_term}%')).all()
    count = len(result)
    response = {
        "count": count,
        "data": result
    }
    return render_template('pages/search_artists.html', results=response, search_term=search_term)


@app.route('/artists/<int:artist_id>')
def show_artist(artist_id):
    artist = Artist.query.get(artist_id)
    artist.upcoming_shows = []
    artist.past_shows = []
    artist.past_shows_count = 0

    shows = Artist.query.join(Show, Show.artist_id == Artist.id).join(Venue, Venue.id == Show.venue_id).add_columns(
        Show.start_time.label('start_time'), Artist.id.label('artist_id'),
        Artist.name.label('artist_name'), Venue.image_link.label('venue_image_link')).filter(
        Artist.id == artist_id).order_by(Show.start_time.desc()).all()
    for show in shows:
        start = show.start_time
        current = datetime.now()
        if start < current:
            artist.past_shows.append(show)
            artist.past_shows_count += 1

        else:
            artist.upcoming_shows.append(show)
            artist.upcoming_shows_count += 1

    return render_template('pages/show_artist.html', artist=artist)


#  Update
#  ----------------------------------------------------------------
@app.route('/artists/<int:artist_id>/edit', methods=['GET'])
def edit_artist(artist_id):
    form = ArtistForm()
    artist = Artist.query.get(artist_id)

    artist.name = form.name.data
    artist.genres = form.genres.data
    artist.image_link = form.image_link.data
    artist.city = form.city.data
    artist.state = form.state.data
    artist.facebook_link = form.facebook_link.data
    artist.phone = form.phone.data
    artist.website = form.website.data


    return render_template('forms/edit_artist.html', form=form, artist=artist)


@app.route('/artists/<int:artist_id>/edit', methods=['POST'])
def edit_artist_submission(artist_id):

    form = ArtistForm()
    artist = Artist.query.get(artist_id)

    if form.validate_on_submit():
        try:
            artist.name = form.name.data
            artist.genres = form.genres.data
            artist.image_link = form.image_link.data
            artist.city = form.city.data
            artist.state = form.state.data
            artist.facebook_link = form.facebook_link.data
            artist.phone = form.phone.data
            artist.website = form.website.data
            flash('Artist named ' + artist.name + ' was successfully edited!')
        except:
            db.session.rollback()
            print(sys.exc_info())
            flash('Please try again Artist ' + artist.name + ' was unsuccessfully edited!')
        finally:
            db.session.close()

    return redirect(url_for('show_artist', artist_id=artist_id))


@app.route('/venues/<int:venue_id>/edit', methods=['GET'])
def edit_venue(venue_id):
    form = VenueForm()
    venue = Venue.query.get(venue_id)

    form.name.data = venue.name
    form.address.data = venue.address
    form.city.data = form.city.data = venue.city
    form.state.data = venue.state
    form.phone.data = venue.phone
    form.website.data = venue.website
    form.facebook_link.data = venue.facebook_link
    form.seeking_talent.data = venue.seeking_talent.data
    form.seeking_description.data = venue.seeking_description.data
    form.image_link.data = venue.image_link.data

    return render_template('forms/edit_venue.html', form=form, venue=venue)


@app.route('/venues/<int:venue_id>/edit', methods=['POST'])
def edit_venue_submission(venue_id):
    venue = Venue.query.get(venue_id)
    form = VenueForm()
    error = False
 #after user clicks on the submit button
    if form.validate_on_submit():
        try:
            venue.name = form.name.data
            venue.phone = form.phone.data
            venue.city = form.city.data
            venue.state = form.state.data
            venue.address = form.address.data
            venue.facebook_link = form.facebook_link.data
            venue.website = form.website.data
            venue.image_link = form.image_link.data
            venue.genres = form.genres.data

            db.session.commit()

        except:
            error = True
            db.session.rollback()
            print(sys.exc_info())

        finally:
            db.session.close()

        if error:
            abort(400)
            flash('Venue with name' + venue.name + ' was not successfully edited!')

        else:
            flash('Venue ' + venue.name + ' was successfully edited!')

            return redirect(url_for('show_venue', venue_id=venue_id))

    # venue record with ID <venue_id> using the new attributes
    return redirect(url_for('show_venue', venue_id=venue_id))


#  Create Artist
#  ----------------------------------------------------------------

@app.route('/artists/create', methods=['GET'])
def create_artist_form():
    form = ArtistForm()
    return render_template('forms/new_artist.html', form=form)


@app.route('/artists/create', methods=['POST'])
def create_artist_submission():
    try:
        artist = Artist(
            name=request.form['name'],
            phone=request.form['phone'],
            city=request.form['city'],
            state=request.form['state'],
            facebook_link=request.form['facebook_link'],
            genres=request.form.getlist('genres'),
            seeking_venue=json.loads(request.form['seeking_venue'].lower()),
            website=request.form['website'],
            image_link=request.form['image_link'],
            seeking_description=request.form['seeking_description']
        )
        db.session.add(artist)
        db.session.commit()
        flash('Artist ' + request.form['name'] + ' was successfully listed!')
    except Exception as e:
        print(e)
        flash('An error occurred. Artist ' + request.form['name'] + ' could not be added')
        db.session.rollback()
    finally:
        db.session.close()
    return render_template('pages/home.html')


#  Shows
#  ----------------------------------------------------------------

@app.route('/shows')
def shows():
    #query shows using join

    data = Show.query.join(Artist, Artist.id == Show.artist_id).join(Venue, Venue.id == Show.venue_id).all()
    response = []

    for show in data:
        response.append({
            "venue_id": show.venue_id,
            "artist_id": show.artist_id,
            "venue_name": show.venue.name,
            "artist_name": show.artist.name,
            "artist_image_link": show.artist.image_link,
            "start_time": str(show.start_time)
        })

    return render_template('pages/shows.html', shows=data)


@app.route('/shows/create')
def create_shows():
    # renders form. do not touch.
    form = ShowForm()
    return render_template('forms/new_show.html', form=form)


@app.route('/shows/create', methods=['POST'])
def create_show_submission():
    try:
        show = Show(
            artist_id=request.form['artist_id'],
            venue_id=request.form['venue_id'],
            start_time=request.form['start_time']
        )
        db.session.add(show)
        db.session.commit()
        flash('Show was successfully added!')
    except Exception as e:
        print(e)
        artist_id = request.form['artist_id']
        flash(f'Please try again! Show with id {artist_id} could not be added')
        db.session.rollback()
    finally:
        db.session.close()
    return render_template('pages/home.html')


@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404


@app.errorhandler(500)
def server_error(error):
    return render_template('errors/500.html'), 500


if not app.debug:
    file_handler = FileHandler('error.log')
    file_handler.setFormatter(
        Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
    )
    app.logger.setLevel(logging.INFO)
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.info('errors')

# ----------------------------------------------------------------------------#
# Launch.
# ----------------------------------------------------------------------------#

# Default port:
if __name__ == '__main__':
    app.run()

# Or specify port manually:
'''
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
'''
