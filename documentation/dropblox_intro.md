Welcome to Dropblox!
===============

In the next few hours, you'll write an AI to play a Tetris variant called Dropblox! We'll provide you with tools to test your program and visualize its performance. After you've had time to develop and test your AI, we'll host a competition to see whose AI can perform the best on a fixed sequence of pieces. We think this contest poses a number of interesting programming challenges, both conceptual and practical.

Getting Started
----
Start by downloading our [getting started materials](https://www.dropbox.com/sh/vmik81v24zfrr0l/XOoKs6mRSU)! You'll use these materials to connect to our game server and test out your AI. In the getting-started subfolder for your operating system, you'll find the following files:

1. `client(.exe)`: The program that communicates with our centralized game server. It will spawn your AI process and forward the moves that you generate to the server.
2. `config.txt`: A file in which you'll specify your team name and password. Used to authenticate the client.
3. `history_server(.exe)`: A program you can run to review the games you've played and watch games you're playing in real-time. Running this server will make your games visible on the [the submission history page](https://playdropblox.com#submission_history).
4. `dropblox_ai`: The executable that the client calls to make Dropblox moves. We've provided a sample AI in Python. To run your AI, replace this file with your program.

The getting-started folder also contains a `samples/` folder. This directory contains helper code and sample AIs in several languages that you can use as a starting point. We've taken care of dealing with I/O and duplicating the game logic for you!

### Create an Account

The first thing you want to do is go to the main [Dropblox site](https://playdropblox.com) and register a new team with a team name and password. Then fill out `config.txt` with your credentials so we can identify you when you connect to the game server.

### Connect to the Game Server

If you're on Mac or Linux, you may need to `chmod +x` the files `history_server`, `client` and `dropblox_ai` to make sure they're executable.

If you're on Windows, you'll need to set two environment variables: `PYTHONPATH` and `PYTHONHOME`. Set them both to `.`. (If you're not sure how to do this, look online or ask for help.)

Open up a terminal and run `./history_server`. You should keep the history server running for the next few hours. It will allow you to view your AI's games at [the submission history page](https://playdropblox.com#submission_history).

Next, run `./client practice`. It should connect to the game server, read your login info from `config.txt`, spawn the `dropblox_ai` process and start a new game! Head over to [the submission history page](https://playdropblox.com#submission_history) and watch the game play out!

Every time you run `./client practice`, a new game will be created and your AI will be invoked to make moves. At the end of the allotted time, when we start official competition rounds, you'll run `./client compete`, which will enter you into these rounds. Don't worry about that for now, though. 

If you have any issues getting `./client practice` to work, please talk to a Dropboxer.

The Rules of Dropblox
----

Dropblox plays much like Tetris. You control one block at a time, and you can translate and rotate it to position it on the board. When you have made your moves, the block will drop as far as it can fall unobstructed, then lock in place. Any rows that are then full are removed from the board.

The main twist introduced in Dropblox are the types of blocks in the game. In addition to tetrominoes, Dropblox includes blocks of arbitrary sizes. The higher your score, the larger the expected size of the blocks that you'll get!

The goal of the game is to score as many points as possible within a 5 minute time limit.

We’ve simplified the rules of the game to make it easier to write an AI. The following is a complete description of all the rules, other than the block generation algorithm.

### Definitions

The board is the grid on which you move the active block. This grid has 33 rows and 12 columns, although only the bottom 24 rows are visualized. When we refer to coordinates on this board, we will always use `i` to refer to the rows and `j` to the columns. The top-left corner of the board is where `i` and `j` equal 0.

The `bitmap` is the current state of the board. `bitmap[i][j]` is non-zero if and only if that square is occupied.

A `block` is defined by the following properties:

1. A `center`, a square on the board, given by an `i` and a `j`. The center is the square about which the block rotates. It is _not_ necessarily a square occupied by the block.
2. A list of offsets, also given by `i` and `j` coordinates. These are the positions of the block’s component squares, relative to its center.

At all times, the board state includes six blocks:

1. One active block, the `block`, which can be moved.
2. A list of five `preview` blocks, which will be the next five active blocks, in order.

### Commands

There are five commands that you can issue to move the active block: `left`, `right`, `up`, `down`, and `rotate`. We define their behavior here. First, we specify what it means for a block to be in a legal position, given by the `check` function.

	boolean check(bitmap, block)
		for (offset in block.offsets)
			(i, j) = (block.center.i + offset.i, block.center.j + offset.j);
			if (i < 0 or i >= 33 or j < 0 or j >= 12 or bitmap[i][j])
				return false;
			return true;
			
Basically, a block is in legal position whenever all of its the component squares are within the bounds of the board and none of them overlap with already occupied cells!

All of the following movement functions assume that the block begins and ends in a valid position! If you are implementing this logic in your AI, you may want to check before and after each command that your block is in a valid position. Alternatively, you may be able to optimize away many of the validity checks.

The `left`, `right`, `up`, and `down` commands are translations with `(i, j)` offsets of `(0, -1)`, `(0, 1)`, `(-1, 0)`, `(1, 0)`, respectively. The general code for a translation is:

	void translate(block, i_offset, j_offset)
		block.center.i += i_offset;
		block.center.j += j_offset;

The `rotate` command rotates a block 90 degrees clockwise around its center. Code for rotate is as follows:

	void rotate(block)
		for (offset in block.offsets) 
			(offset.i, offset.j) = (offset.j, -offset.i);

When you wish to end your turn, your AI process should terminate. A `drop` command will be append to the end of your list of moves.

Code for the `drop` command is as follows. Note that this code assumes that the block is initially in a valid position, and that it mutates both the bitmap and the block.

	void drop(bitmap, block)
		while (check(bitmap, block))
			block.center.i += 1
		block.center.i -= 1
		for (offset in block.offsets)
			// We could set this cell to be any non-zero number. In the actual 
			// implementation, the bitmap contains color information.
			bitmap[block.center.i + offset.i][block.center.j + offset.j] = 1
		remove_full_rows(bitmap)

As shown in this snippet, after a block is placed, any full rows are removed from the board. It is at this stage that you score points! You will get `2^n - 1` points for clearing `n` rows with one drop. Code for this procedure is as follows:

	void remove_full_rows(bitmap)
		bitmap = [row for row in bitmap if not all(row)]
		num_rows_removed = 33 - len(bitmap)
		bitmap = num_rows_removed*[12*[0]] + bitmap
		score += (1 << num_rows_removed) - 1

And that’s (nearly) the full rule-set of Dropblox! Feel free to ask questions.

Building Your AI
----

### dropblox_ai Program Specification

For each turn in the game, the client process will spawn your `dropblox_ai` executable, passing in the state of the game as a command line argument. Your executable should print a list of commands to stdout, each one on a new line. When the `dropblox_ai` executable terminates, the turn will be over. The game server will execute the given commands to move the block, then drop it into place on the board. The server will then request the next move, and the client will spawn a new AI process with the new game state.

This loop will continue until you run out of space on the board or the 5 minute time period for the game is over. When the game ends on time, any commands your AI has printed to stdout for the current move will be ignored.


#### Input
Your `dropblox_ai` program should accept two command-line arguments: 

1. A JSON-encoded string modeling the game state. Here is an example of the input:
> {"bitmap": [[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]], "state": "playing", "score": 0, "preview": [{"type": 5, "center": {"i": 8, "j": 6}, "offsets": [{"i": 0, "j": 0}, {"i": -1, "j": 0}, {"i": 1, "j": 0}, {"i": 1, "j": -1}]}, {"type": 22, "center": {"i": 8, "j": 6}, "offsets": [{"i": 0, "j": 0}, {"i": -1, "j": 0}, {"i": 1, "j": 0}, {"i": 0, "j": -1}, {"i": 1, "j": 1}]}, {"type": 3, "center": {"i": 9, "j": 6}, "offsets": [{"i": 0, "j": 0}, {"i": -1, "j": 0}, {"i": 0, "j": 1}]}, {"type": 4, "center": {"i": 7, "j": 6}, "offsets": [{"i": 0, "j": 0}, {"i": -1, "j": 0}, {"i": 1, "j": 0}, {"i": 2, "j": 0}]}, {"type": 12, "center": {"i": 8, "j": 6}, "offsets": [{"i": 0, "j": 0}, {"i": -1, "j": 0}, {"i": -2, "j": 0}, {"i": 1, "j": 0}, {"i": 1, "j": -1}]}], "block": {"type": 4, "center": {"i": 7, "j": 6}, "offsets": [{"i": 0, "j": 0}, {"i": -1, "j": 0}, {"i": 1, "j": 0}, {"i": 2, "j": 0}]}}

2. The number of seconds remaining in the game, a float.

#### Output

We are expecting your AI program to print its moves to standard out. The following are considered valid move strings:

1. `left`
2. `right`
3. `up`
4. `down`
5. `rotate`

Your AI must print one of these strings, immediately followed by a newline character, in order to be sent to our server. We recommend you flush stdout after printing, to ensure the move is sent to the server immediately. This will allow you to submit moves in a streaming fashion, so that if you hit the timeout, you'll at least have made some move with the current block.

If you print anything else to stdout, our `client` program will simply print it to stdout itself.

Sample AIs
----

We have provided reference implementations in 3 different languages to help you get started quickly. You will find these implementations inside the `samples/` directory of the getting-started materials. Each sample comes with a `README` file explaining how to compile (if necessary) and run the code.

These reference implementations take care of a lot of the details of setup, including parsing the JSON and generating reasonable objects to represent the current game state. They also provide helper methods for handling pieces, making moves, and computing the new board after a drop. We recommend that you start with them! However, these AIs won't score many points. The reference implementations simply move the piece as far left as it can go -- that's it!
