refactor
Python 3 Webserver for browsing downloaded Fur Affinity posts quickly and easily.
[Video example](https://www.youtube.com/watch?v=W1tM0ZRNgf4)

# Requirements
* Python 3
* Fur Affinity posts (images & data), works with [getFA](https://github.com/CodedCells/getfa)

# Setup
1. Place all files in a folder.
2. Create `i` and `p` folders.
3. Place all images in `i`.
4. Place all html pages in `p`.
5. Start `fadsrv.py` and let it build `fadata.json`.
6. Navigate to `127.0.0.1:6970` in your web browser.

# Features
* Posts grouped by artist
* Posts grouped by keywords
* Recently updated artists
* Partially "seen" artists (where some posts have been "marked as seen" but not all).
* **Choose Your Own Adventure** aka either mark as passed or to be passed later.
* Artist name search
* Shuffled list of arists (aka suprise me)

# Terminology
* `seen` - You've looked at the image and mark it as such.
* `ref`er - want to look at it again at some point.
* `rem`ove - for stuff you might have missed and not want to keep.
* `passed` - When you've looked on Fur Affinity and got everything you want.
* `l8r` - I'll look at that artist later (aka 6134 posts is a lot to look at atm)

## WIP
* Fix code repetition
* Make code more readable
* Improve functionality
* Decrease performance intensivity
* Configurability
