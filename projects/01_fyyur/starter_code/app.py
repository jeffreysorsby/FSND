#----------------------------------------------------------------------------#
# Imports
#----------------------------------------------------------------------------#

import json
import dateutil.parser
import babel
from flask import Flask, render_template, request, Response, flash, redirect, url_for, jsonify
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import logging
from logging import Formatter, FileHandler
from flask_wtf import Form
from forms import *
import sys
from datetime import datetime

#----------------------------------------------------------------------------#
# App Config.
#----------------------------------------------------------------------------#

app = Flask(__name__)
moment = Moment(app)
app.config.from_object('config')
db = SQLAlchemy(app)

migrate = Migrate(app, db)

#----------------------------------------------------------------------------#
# Models.
#----------------------------------------------------------------------------#

class Venue(db.Model):
    __tablename__ = 'Venue'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable = False)
    city = db.Column(db.String, nullable = False)
    state = db.Column(db.String, nullable = False)
    address = db.Column(db.String, nullable = False)
    phone = db.Column(db.String)
    genres = db.Column(db.ARRAY(db.String), nullable = False)
    image_link = db.Column(db.String)
    facebook_link = db.Column(db.String)
    website = db.Column(db.String)
    seeking_talent = db.Column(db.Boolean, nullable = False, default = False)
    seeking_description = db.Column(db.String, default = 'Not looking for talent')
    shows = db.relationship('Show', backref = 'venue', passive_deletes = True, lazy = True)

class Artist(db.Model):
    __tablename__ = 'Artist'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable = False)
    city = db.Column(db.String(120), nullable = False)
    state = db.Column(db.String(120), nullable = False)
    phone = db.Column(db.String(120))
    genres = db.Column(db.ARRAY(db.String), nullable = False)
    image_link = db.Column(db.String(500))
    facebook_link = db.Column(db.String(120))
    website = db.Column(db.String(120))
    seeking_venue = db.Column(db.Boolean, nullable = False, default = False)
    seeking_description = db.Column(db.String, default = 'Not looking for venues')
    shows = db.relationship('Show', backref = 'artist', passive_deletes = True, lazy = True)

class Show(db.Model):
    __tablename__: 'Show'

    id = db.Column(db.Integer, primary_key = True)
    artist_id = db.Column(db.Integer, db.ForeignKey('Artist.id', ondelete = 'CASCADE'), nullable = False)
    venue_id = db.Column(db.Integer, db.ForeignKey('Venue.id', ondelete = 'CASCADE'), nullable = False)
    start_time = db.Column(db.DateTime, nullable=False)

#----------------------------------------------------------------------------#
# Filters.
#----------------------------------------------------------------------------#

def format_datetime(value, format='medium'):
  date = dateutil.parser.parse(value)
  if format == 'full':
      format="EEEE MMMM, d, y 'at' h:mma"
  elif format == 'medium':
      format="EE MM, dd, y h:mma"
  return babel.dates.format_datetime(date, format)

app.jinja_env.filters['datetime'] = format_datetime

#----------------------------------------------------------------------------#
# Controllers.
#----------------------------------------------------------------------------#

@app.route('/')
def index():
  return render_template('pages/home.html')


#  Venues
#  ----------------------------------------------------------------

@app.route('/venues')
def venues():
  data = []
  locations = set()
  venues = Venue.query.all()

  for venue in venues:
    locations.add((venue.city, venue.state))

  for location in locations:
    data.append({
      'city': location[0],
      'state': location[1],
      'venues': []
    })
  
  for venue in venues:
    num_upcoming_shows = 0

    shows = Show.query.filter_by(venue_id = venue.id).all()
    now = datetime.now()
    for show in shows:
      if show.start_time > now:
        num_upcoming_shows += 1

    for location in data:
      if venue.state == location['state'] and venue.city == location['city']:
        location['venues'].append({
          'id': venue.id,
          'name': venue.name,
          'num_upcoming_shows': num_upcoming_shows
        })

  return render_template('pages/venues.html', areas=data)

@app.route('/venues/search', methods=['POST'])
def search_venues():
  venue_search = request.form.get('search_term')
  data = []
  venues = Venue.query.filter(Venue.name.ilike('%' + venue_search + '%')).all()
  num_upcoming_shows = 0

  for venue in venues:
    shows = Show.query.filter(Show.venue_id == venue.id)
    for show in shows:
      if(show.start_time > datetime.now()):
        num_upcoming_shows += 1
    
    data.append({
      'id': venue.id,
      'name': venue.name,
      'num_upcoming_shows': num_upcoming_shows
    })

  response={
    "count": len(venues),
    "data": data
  }
  return render_template('pages/search_venues.html', results=response, search_term=request.form.get('search_term', ''))

@app.route('/venues/<int:venue_id>')
def show_venue(venue_id):
  venue = Venue.query.filter(Venue.id == venue_id).one()
  list_shows = Show.query.filter(Show.venue_id == venue_id)
  past_shows = []
  upcoming_shows = []
  data = []

  for show in list_shows:
    artist = db.session.query(Artist.name, Artist.image_link).filter(Artist.id == show.artist_id).one()
    show_add = {
      'artist_id': show.artist_id,
      'artist_name': artist.name,
      'artist_image_link': artist.image_link,
      'start_time': str(show.start_time)
    }

    if(show.start_time < datetime.now()):
      past_shows.append(show_add)
    else:
      upcoming_shows.append(show_add)

  data = {
      "id": venue.id,
      "name": venue.name,
      "genres": ''.join(list(filter(lambda x : x!= '{' and x!='}', venue.genres ))).split(','),
      "address": venue.address,
      "city": venue.city,
      "state": venue.state,
      "phone": venue.phone,
      "facebook_link": venue.facebook_link,
      "image_link": venue.image_link,
      "website": venue.website,
      "past_shows": past_shows,
      "upcoming_shows": upcoming_shows,
      "seeking_talent": venue.seeking_talent,
      "seeking_description": venue.seeking_description,
      "past_shows_count": len(past_shows),
      "upcoming_shows_count": len(upcoming_shows)
    }

  return render_template('pages/show_venue.html', venue = data)

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
    venue_boolean = request.form.get('seeking_talent')
    vb = False
    if venue_boolean == 'y':
        vb = True
    new_venue = Venue(
      name = request.form.get('name'),
      city = request.form.get('city'),
      state = request.form.get('state'),
      address = request.form.get('address'),
      phone = request.form.get('phone'),
      genres = request.form.getlist('genres'),
      facebook_link = request.form.get('facebook_link'),
      website = request.form.get('website'),
      seeking_talent = vb,
      seeking_description = request.form.get('seeking_description'),
      image_link = request.form.get('image_link')
    )
    db.session.add(new_venue)
    db.session.commit()
  except:
    error = True
    db.session.rollback()
    print(sys.exc_info())
  finally:
    db.session.close()
  if not error:
    flash('Venue ' + request.form['name'] + ' was successfully listed!')
  else:
    flash('An error ocurred, ' + request.form['name'] + ' was not successfully listed!')

  return render_template('pages/home.html')

@app.route('/venues/<venue_id>', methods=['DELETE'])
def delete_venue(venue_id):
  error = False
  try:
    venue = Venue.query.filter(Venue.id == venue_id).one()
    db.session.delete(venue)
    name = venue.name
    db.session.commit()
  except:
    error = True
    db.session.rollback()
  finally:
    db.session.close()

  if not error:
    flash('Venue ' + name + ' was successfully deleted!')
  else:
    flash('An error ocurred, ' + name + ' was not successfully deleted!')

  return jsonify({'success': True})

#  Artists
#  ----------------------------------------------------------------
@app.route('/artists')
def artists():
  artists = Artist.query.all()
  data = []

  for artist in artists:
    listing = {
      'id': artist.id,
      'name': artist.name
    }
    data.append(listing)

  return render_template('pages/artists.html', artists=data)

@app.route('/artists/search', methods=['POST'])
def search_artists():
  artist_search = request.form.get('search_term')
  data = []
  artists = Artist.query.filter(Artist.name.ilike('%' + artist_search + '%')).all()
  num_upcoming_shows = 0

  for artist in artists:
    shows = Show.query.filter(Show.artist_id == artist.id)
    for show in shows:
      if(show.start_time > datetime.now()):
        num_upcoming_shows += 1
    
    data.append({
      'id': artist.id,
      'name': artist.name,
      'num_upcoming_shows': num_upcoming_shows
    })

  response={
    "count": len(artists),
    "data": data
  }
  return render_template('pages/search_artists.html', results=response, search_term=request.form.get('search_term', ''))

@app.route('/artists/<int:artist_id>')
def show_artist(artist_id):
  artist = Artist.query.filter(Artist.id == artist_id).one()
  list_shows = Show.query.filter(Show.artist_id == artist_id)
  past_shows = []
  upcoming_shows = []
  data = []

  for show in list_shows:
    venue = db.session.query(Venue.name, Venue.image_link).filter(Venue.id == show.venue_id).one()
    show_add = {
        'venue_id': show.venue_id,
        'venue_name': venue.name,
        'venue_image_link': venue.image_link,
        'start_time': str(show.start_time)
      }
    if(show.start_time > datetime.now()):
      upcoming_shows.append(show_add)
    else:
      past_shows.append(show_add)
  
  data = {
    'id': artist.id,
    'name': artist.name,
    'genres': ''.join(list(filter(lambda x : x!= '{' and x!='}', artist.genres ))).split(','),
    'city': artist.city,
    'state': artist.state,
    'phone': artist.phone,
    'facebook_link': artist.facebook_link,
    'image_link': artist.image_link,
    'website': artist.website,
    'past_shows': past_shows,
    'upcoming_shows': upcoming_shows,
    'seeking_venue': artist.seeking_venue,
    'seeking_description': artist.seeking_description,
    'past_shows_count': len(past_shows),
    'upcoming_shows_count': len(upcoming_shows)
  }

  return render_template('pages/show_artist.html', artist = data)

#  Update
#  ----------------------------------------------------------------
@app.route('/artists/<int:artist_id>/edit', methods=['GET'])
def edit_artist(artist_id):
  

  artist = Artist.query.filter(Artist.id == artist_id).one()
  form = ArtistForm(obj=artist)

  return render_template('forms/edit_artist.html', form = form, artist = artist)

@app.route('/artists/<int:artist_id>/edit', methods=['POST'])
def edit_artist_submission(artist_id):
  form = ArtistForm(request.form)
  artist = Artist.query.filter(Artist.id == artist_id).one()
  error = False

  try:
    artist.name = request.form.get('name')
    artist.city = request.form.get('city')
    artist.state = request.form.get('state')
    artist.phone = request.form.get('phone')
    artist.genres = request.form.getlist('genres')
    artist.facebook_link = request.form.get('facebook_link')
    artist.image_link = request.form.get('image_link')
    artist.website = request.form.get('website')
    venue_boolean = request.form.get('seeking_venue')
    vb = False
    if venue_boolean == 'y':
      vb = True
    artist.seeking_venue = vb
    artist.seeking_description = request.form.get('seeking_description')
    db.session.commit()
  except:
    db.session.rollback()
    error = True
  finally:
    db.session.close()

  if not error:
    flash('Artist ' + request.form['name'] + ' was successfully updated!')
  else:
    flash('An error occured, artist ' + request.form['name'] + ' was not successfully updated!')
  
  return redirect(url_for('show_artist', artist_id=artist_id))

@app.route('/artists/<int:artist_id>', methods=['DELETE'])
def delete_artist(artist_id):
  error = False
  try:
    artist = Artist.query.filter(Artist.id == artist_id).one()
    db.session.delete(artist)
    name = artist.name
    db.session.commit()
  except:
    error = True
    db.session.rollback()
  finally:
    db.session.close()

  if not error:
    flash('Artist ' + name + ' was successfully deleted!')
  else:
    flash('An error ocurred, ' + name + ' was not successfully deleted!')

  return jsonify({'success': True})

@app.route('/venues/<int:venue_id>/edit', methods=['GET'])
def edit_venue(venue_id):
  venue = Venue.query.filter(Venue.id == venue_id).one()
  form = VenueForm(obj=venue)

  return render_template('forms/edit_venue.html', form=form, venue=venue)

@app.route('/venues/<int:venue_id>/edit', methods=['POST'])
def edit_venue_submission(venue_id):
  form = VenueForm(request.form)
  error = False
  venue = Venue.query.filter(Venue.id == venue_id).one()

  try:
    venue.name = request.form.get('name')
    venue.city = request.form.get('city')
    venue.state = request.form.get('state')
    venue.address = request.form.get('address')
    venue.genres = request.form.getlist('genres')
    venue.facebook_link = request.form.get('facebook_link')
    venue.image_link = request.form.get('image_link')
    venue.website = request.form.get('website')
    venue_boolean = request.form.get('seeking_talent')
    vb = False
    if venue_boolean == 'y':
      vb = True
    venue.seeking_talent = vb
    venue.seeking_description = request.form.get('seeking_description')
    db.session.commit()
  except:
    error = True
    db.session.rollback()
  finally:
    db.session.close()

  if not error:
    flash('Venue ' + request.form['name'] + ' was successfully updated!')
  else:
    flash('An error occured, Venue ' + request.form['name'] + ' was not successfully updated!')
  

  return redirect(url_for('show_venue', venue_id=venue_id))

#  Create Artist
#  ----------------------------------------------------------------

@app.route('/artists/create', methods=['GET'])
def create_artist_form():
  form = ArtistForm()
  return render_template('forms/new_artist.html', form=form)

@app.route('/artists/create', methods=['POST'])
def create_artist_submission():
  error = False
  try:
    venue_boolean = request.form.get('seeking_venue')
    vb = False
    if venue_boolean == 'y':
        vb = True
    new_artist = Artist(
      name = request.form.get('name'),
      city = request.form.get('city'),
      state = request.form.get('state'),
      phone = request.form.get('phone'),
      genres = request.form.getlist('genres'),
      facebook_link = request.form.get('facebook_link'),
      image_link = request.form.get('image_link'),
      website = request.form.get('website'),
      seeking_venue = vb,
      seeking_description = request.form.get('seeking_description')
    )
    db.session.add(new_artist)
    db.session.commit()
  except:
    db.session.rollback()
    error = True
    print(sys.exc_info())
  finally:
    db.session.close()
  if not error:
    flash('Artist ' + request.form['name'] + ' was successfully listed!')
  else:
    flash('An error occured, artist ' + request.form['name'] + ' was not successfully listed!')

  return render_template('pages/home.html')


#  Shows
#  ----------------------------------------------------------------

@app.route('/shows')
def shows():

  shows = Show.query.all()
  data = []
  for show in shows:
    listing = {
      'venue_id': show.venue_id,
      'venue_name': show.venue.name,
      'artist_id': show.artist_id,
      'artist_name': show.artist.name,
      'artist_image_link': show.artist.image_link,
      'start_time': str(show.start_time)
    }
    data.append(listing)

  return render_template('pages/shows.html', shows=data)

@app.route('/shows/create')
def create_shows():
  # renders form. do not touch.
  form = ShowForm()
  return render_template('forms/new_show.html', form=form)

@app.route('/shows/create', methods=['POST'])
def create_show_submission():
  error = False

  try:
    new_show = Show(
      artist_id = request.form.get('artist_id'),
      venue_id = request.form.get('venue_id'),
      start_time = format_datetime(request.form.get('start_time'))
    )
    db.session.add(new_show)
    db.session.commit()
  except:
    error = True
    db.session.rollback()
    print(sys.exc_info())
  finally:
    db.session.close()
  if not error:
    flash('Show was successfully listed!')
  else:
      flash('An error ocurred, show was not successfully listed!')
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

#----------------------------------------------------------------------------#
# Launch.
#----------------------------------------------------------------------------#

# Default port:
if __name__ == '__main__':
    app.run()

# Or specify port manually:
'''
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
'''
