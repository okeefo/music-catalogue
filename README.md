# music-catalogue

STATUS = database integration in progress. 

As there is only a single contributor, me, and there is no other contributor, I will not be using a git workflow.  I will be using a single branch and will be committing to the main branch.

Any other branches created are simple to try out new features.

I have yet to create a version and as this is a hobby project i may not do so for some time.

For ideas, bugs and feature requests please use the issues tab.


## History

Music Catalogue started as a personal project to streamline the process of backing up vinyl records to a PC. The initial process involved several manual steps:

1. Record an LP into Audacity as a single recording at 45rpm to speed up recording.
2. Remove needle drops and clicks from flipping the record over.
3. Slow the recording to the original speed of 33rpm.
4. Amplify the recording to improve volume.
5. Mark the start and end of each track.
6. Export the tracks as WAV files.
7. Open tracks in MP3 Tag.
8. Find the release ID on Discogs.
9. Tag the tracks with the release ID.
10. Rename the file name of the tracks - catalog id - Label - artist - title etc.
11. Copy the tracks to a folder with the Label as the name.

The initial goal was to create a single UI with two file explorers for easy file management. This idea evolved, leading to the addition of features like track playback, tag display, artwork display, and more.

The current process is much more streamlined:

1. Record an LP into Audacity as a single recording at 45rpm to speed up recording.
2. Remove needle drops and clicks from flipping the record over.
3. Find the release ID on Discogs.
4. Save the file name with the release ID and the original speed.

The rest of the process:

* Amplifying the recording
* Slowing down the recording
* Splitting the recording into tracks
* Tagging the tracks based on the Discogs ID
* Adding artwork
* Renaming filenames of the tracks
* Repacking the tracks into a folder by label

is now automated and can be done with a single click from within the application. Each operation can also be performed separately if needed.

## Features

Music Catalogue is packed with features that simplify the organisation of a music collection:

* **Automated Processes**: Amplify recordings, slow down recordings, split recordings into tracks, tag tracks, add artwork, rename track filenames, and repack tracks into folders by label - all with a single click.
* **Manual Control**: Each operation can also be performed separately for maximum control.
* **Track Playback**: Listen to your tracks directly from the application.
* **Tag and Artwork Display**: View track tags and artwork.
* **File Management**: Easily manage your music files with two file explorers.
* **Trim**: Remove silence from the start of the track - (experimental/beta testing)
* **Discogs Integration**: Find release IDs on Discogs.
* **3rd Party**: Opens files in Audacity for editing, Mp3Tag, VLC Player and MediaInfo - you must have these installed.

## Installation
This is a python application and requires a python environment.  It runs only on windows.  It has been tested on windows 11 and 10.  It should run on windows 7 and 8.

Third party DLLs and executables are included and the path is automatically updated for the session when the application is run.  These DLLs and executables are required for the wav file processing.

for tagging install the following:

pip install mutagen
pip install winshell
pip install pywin32
pip install pytaglib
pip install send2trash
pip install discogs_client
pip install pydub
pip install PyQt5
pip install pydantic
pip install qtpy
pip install pydantic
pip install numpy

The application has been tested with python 3.10.4.  It should work with python 3.10 and later. 

## Upcoming features:

* TRIM - remove silence from the start and end of the track - in progress
  * Currently implemented as a separate process.  It will be integrated into the main process once more testing has completed.
  * I added this because the beat grid editor in Engine DJ is rubbish and i couldn't move the to the first bar to the start of the track
  * The Trim process is a bit harsh, I want to give a few a ms before the start of the track but SOX doesn't seem to be able to do this.
  * I can have written some code to do this but not keen to commit this yet. It does work well though and I'll probably get back to the DB work ;)
* Database options - scan the music collection and create a database of the music collection  - in progress.
* Configuration manager to make it easier to update the config file - change the defaults


## Getting Started

Run the main_window.py script to start

## Contributing

:TODO

## License

This project is licensed under the terms of the MIT License. See the [LICENSE-MIT](LICENSE-MIT)  file for details.
