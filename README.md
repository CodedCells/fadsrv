Python 3 tool set and web server for downloading and browsing Fur Affinity posts in customisable lists, quickly and easily.

[Outdated Video example](https://www.youtube.com/watch?v=W1tM0ZRNgf4)

This project is a work in progress, fixing up old janky code I wrote hastily.

# Requirements
* Python 3
* Fur Affinity posts (images & data), works with [getFA](https://github.com/CodedCells/getfa)
* Some knowledge of Python 3

# Setup
1. Create a directory for the scripts to work in
2. Either configure getFA or add files: images in `i/` and pages in `p/`
3. (optional) Create `data/` to keep server data organised
4. Run `main.py` and let it build metadata
5. Navigate to `127.0.0.1:6970` in your web browser

# Features
* Posts grouped by users, keywords, folders and customisable lists
* User, keyword and folder search
* Customisable lists, for users and posts
* Customisable buttons, dropdowns and other ways to organise users and posts.
* Optimised data handling, enabling fast change saving

# WIP
* Make set handling less hardcoded
* Optimise use of global variables
* Fix legacy code issues rather than working around them
* Make code more readable
* Improve functionality
* Configurability
