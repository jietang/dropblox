Welcome to Dropblox!
===============

In the next few hours, you'll write an AI to play a Tetris variant called Dropblox! We'll provide you with tools to test your program and visualize its performance. After you've had time to develop and test your AI, we'll host a competition to see whose AI can perform the best on a fixed sequence of pieces. We think this contest poses a number of interesting programming challenges, both conceptual and practical.

Getting Started
----
Download our [getting started materials](https://www.dropbox.com/sh/vmik81v24zfrr0l/XOoKs6mRSU) to get the code you'll need to connect to our game server and test out your AI. Inside the getting started folder, you'll find the following:

1. `client(.exe)`: The program that communicates with our centralized game server. It will spawn your AI process and forward moves that you generate to our remote server.
2. `config.txt`: Specifies the team name and password to use when authing with the game server.
3. `history_server(.exe)`: A program you can run to view the history of games you've played and view move-by-move playback of your AI's decisions.
4. `dropblox_ai`: The executable program you will be writing to make Dropblox moves. We've provided a small sample written in Python.
5. `samples/`: A directory of helper code and sample AIs to help you understand the game logic and I/O specification for your AI.

### Create an Account

The first thing you want to do is go to the main [Dropblox site](https://playdropblox.com) and register a new team with a team name and password. Then fill out `config.txt` with your credentials so we can identify you when you connect to the game server.

### Connect to the Game Server

Before you start, you may need to `chmod +x` the files `history_server`, `client` and `dropblox_ai`, to make sure they're all executable.

Windows users: You'll also need to set two environment variables (ask for help or look online if you're not sure how): `PYTHONPATH` and `PYTHONHOME`. These should both be set to `.`

Open up a terminal and run `./history_server`. You should just keep the history server running for the next few hours. It will allow you to view your game history from [https://playdropblox.com#submission_history](https://playdropblox.com#submission_history).

Next, run `./client practice`. It should connect to the game server, read your login info from `config.txt`, spawn the `dropblox_ai` process and start a new game! Head over to [https://playdropblox.com#submission_history](https://playdropblox.com#submission_history) and see the game being played!

Every time you run `./client practice`, a new game will be created and your AI will be invoked to ask for moves. At the end of the allotted time when we actually start the competition, you'll run `./client compete`, which will actually enter you into the competition rounds, but don't worry about that for now. 

If you have any issues getting `./client practice` to work, please talk to a Dropboxer.


The Rules of Dropblox
----

Dropblox plays much like Tetris. You control one block at a time, and you can translate and rotate it to position it on the board. When you have made your moves, the block will drop as far as it can fall unobstructed, then lock in place. Any rows that are then full are removed from the board.

The main twist introduced in Dropblox are the types of blocks in the game. In addition to tetrominoes, Dropblox includes blocks of arbitrary size. The higher your score, the larger the expected size of the blocks you get!

The goal of the game is to score as many points as possible in a 5 minute time limit.

We’ve simplified the rules of the game to make it easier to write an AI. The following is a complete description of all the rules other than the block generation algorithm.

### Definitions

The board is the grid on which you move the active block. This grid has 33 rows and 12 columns, although only the bottom 24 rows are visualized. When we refer to coordinates on this board, we will always use `i` to refer to the rows and `j` to the columns. The top-left corner of the board is where `i` and `j` equal 0.

The `bitmap` is the current state of the board. `bitmap[i][j]` is non-zero if and only if that square is occupied.

A `block` is defined by the following properties:

1. A `center`, a square on the board, given by an `i` and a `j`. The center is the square about which the block rotates. It is _not_ necessarily a square occupied by the block.
2. A list of offsets, given by `i` and `j` coordinates. These are the positions of the block’s component squares, relative to its center.

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
			
Basically, whenever all the components of a block are within the bounds of the board and don't overlap an already occupied slot, the block is in a legal position!

All of the following movement functions assume that the block begins and ends in a valid position! If you are implementing this logic in your AI, you may want to check before and after each command that your block is in a valid position. Alternatively, you may be able to optimize away many of the validity checks.

The `left`, `right`, `up`, and `down` commands are translations with `(i, j)` offsets of `(0, -1)`, `(0, 1)`, `(-1, 0)`, `(1, 0)`, respectively. The general code for a translation is:

	void translate(block, i_offset, j_offset)
		block.center.i += i_offset;
		block.center.j += j_offset;

The `rotate` command rotates a block 90 deg. around its center. Code for rotate is as follows:

	void rotate(block)
		for (offset in block.offsets) 
			(offset.i, offset.j) = (offset.j, -offset.i);

When you wish to end your turn, your AI process should terminate. At the end of your list of moves, a `drop` command will be issued.

Code for the `drop` command is as follows (note that it assumes the block is initially in a valid position, and that it mutates both the bitmap and the block):

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

For each turn in the game, your `dropblox_ai` process will be spawned and given the state of the game. It will then be expected to print a list of commands to stdout. When the `dropblox_ai` process finishes, the turn will be considered over. The game server will execute the commands provided, then drop the block into its final position. The game server will then request the next move and a new instance of your AI process will be spawned with the new game state. This will continue until the 5 minute time period for the game is over. When the 5 minutes expires, your AI process will be terminated and any moves printed to stdout will be accepted as your final turn.


#### Input
Your `dropblox_ai` program should accept two command-line arguments: 

1. A JSON-encoded string modeling the game state. Here is an example of the input:
> {"bitmap": [[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]], "state": "playing", "score": 0, "preview": [{"type": 5, "center": {"i": 8, "j": 6}, "offsets": [{"i": 0, "j": 0}, {"i": -1, "j": 0}, {"i": 1, "j": 0}, {"i": 1, "j": -1}]}, {"type": 22, "center": {"i": 8, "j": 6}, "offsets": [{"i": 0, "j": 0}, {"i": -1, "j": 0}, {"i": 1, "j": 0}, {"i": 0, "j": -1}, {"i": 1, "j": 1}]}, {"type": 3, "center": {"i": 9, "j": 6}, "offsets": [{"i": 0, "j": 0}, {"i": -1, "j": 0}, {"i": 0, "j": 1}]}, {"type": 4, "center": {"i": 7, "j": 6}, "offsets": [{"i": 0, "j": 0}, {"i": -1, "j": 0}, {"i": 1, "j": 0}, {"i": 2, "j": 0}]}, {"type": 12, "center": {"i": 8, "j": 6}, "offsets": [{"i": 0, "j": 0}, {"i": -1, "j": 0}, {"i": -2, "j": 0}, {"i": 1, "j": 0}, {"i": 1, "j": -1}]}], "block": {"type": 4, "center": {"i": 7, "j": 6}, "offsets": [{"i": 0, "j": 0}, {"i": -1, "j": 0}, {"i": 1, "j": 0}, {"i": 2, "j": 0}]}}

2. The number of seconds remaining in the game.

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

We have provided reference implementations in 3 different languages to help you get started quickly. You will find these implementations inside the `samples/` directory. Each one has a `README` file explaining how to compile (if necessary) and run.  These reference implementations take care of much of the hairy setup (parsing the JSON, generating reasonable objects to represent the current game state), and provide helper methods for handling pieces, making moves, and generating new boards. We recommend that you use them!  Right now, the reference implementations simply move a piece as far left as it can go -- that's it!
