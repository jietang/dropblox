#include "json/reader.h"
#include "json/elements.h"

//#include <fstream>
#include <cmath>
#include <sstream>
#include <vector>

using namespace json;
using namespace std;

#define ROWS 33
#define COLS 12
#define PREVIEW_SIZE 5

typedef int Bitmap[ROWS][COLS];
typedef pair<const Bitmap*, float> ScoredBitmap;

struct ScoredBitmap_comp {
  bool operator()(ScoredBitmap const& left, ScoredBitmap const& right){
    return left.second > right.second;
  }
};

/*
Move mapping:
  0: drop,
  1: rotate,
  2: left,
  3: right
*/

#define NUM_MOVES 44
#define MOVE_SIZE 10

int moves[NUM_MOVES][MOVE_SIZE] = {
{0, 0, 0, 0, 0, 0, 0, 0, 0, 0},
{2, 0, 0, 0, 0, 0, 0, 0, 0, 0},
{2, 2, 0, 0, 0, 0, 0, 0, 0, 0},
{2, 2, 2, 0, 0, 0, 0, 0, 0, 0},
{2, 2, 2, 2, 0, 0, 0, 0, 0, 0},
{2, 2, 2, 2, 2, 0, 0, 0, 0, 0},
{3, 0, 0, 0, 0, 0, 0, 0, 0, 0},
{3, 3, 0, 0, 0, 0, 0, 0, 0, 0},
{3, 3, 3, 0, 0, 0, 0, 0, 0, 0},
{3, 3, 3, 3, 0, 0, 0, 0, 0, 0},
{3, 3, 3, 3, 3, 0, 0, 0, 0, 0},
{1, 0, 0, 0, 0, 0, 0, 0, 0, 0},
{1, 2, 0, 0, 0, 0, 0, 0, 0, 0},
{1, 2, 2, 0, 0, 0, 0, 0, 0, 0},
{1, 2, 2, 2, 0, 0, 0, 0, 0, 0},
{1, 2, 2, 2, 2, 0, 0, 0, 0, 0},
{1, 2, 2, 2, 2, 2, 0, 0, 0, 0},
{1, 3, 0, 0, 0, 0, 0, 0, 0, 0},
{1, 3, 3, 0, 0, 0, 0, 0, 0, 0},
{1, 3, 3, 3, 0, 0, 0, 0, 0, 0},
{1, 3, 3, 3, 3, 0, 0, 0, 0, 0},
{1, 3, 3, 3, 3, 3, 0, 0, 0, 0},
{1, 1, 0, 0, 0, 0, 0, 0, 0, 0},
{1, 1, 2, 0, 0, 0, 0, 0, 0, 0},
{1, 1, 2, 2, 0, 0, 0, 0, 0, 0},
{1, 1, 2, 2, 2, 0, 0, 0, 0, 0},
{1, 1, 2, 2, 2, 2, 0, 0, 0, 0},
{1, 1, 2, 2, 2, 2, 2, 0, 0, 0},
{1, 1, 3, 0, 0, 0, 0, 0, 0, 0},
{1, 1, 3, 3, 0, 0, 0, 0, 0, 0},
{1, 1, 3, 3, 3, 0, 0, 0, 0, 0},
{1, 1, 3, 3, 3, 3, 0, 0, 0, 0},
{1, 1, 3, 3, 3, 3, 3, 0, 0, 0},
{1, 1, 1, 0, 0, 0, 0, 0, 0, 0},
{1, 1, 1, 2, 0, 0, 0, 0, 0, 0},
{1, 1, 1, 2, 2, 0, 0, 0, 0, 0},
{1, 1, 1, 2, 2, 2, 0, 0, 0, 0},
{1, 1, 1, 2, 2, 2, 2, 0, 0, 0},
{1, 1, 1, 2, 2, 2, 2, 2, 0, 0},
{1, 1, 1, 3, 0, 0, 0, 0, 0, 0},
{1, 1, 1, 3, 3, 0, 0, 0, 0, 0},
{1, 1, 1, 3, 3, 3, 0, 0, 0, 0},
{1, 1, 1, 3, 3, 3, 3, 0, 0, 0},
{1, 1, 1, 3, 3, 3, 3, 3, 0, 0}
};

struct Point {
  int i;
  int j;
};

struct Block {
  Point center;
  int num_squares;
  Point squares[10];
  // Mutable state used to place the block in various positions.
  Point offset;
  int angle;
};

void print_bitmap(const Bitmap& bitmap) {
  for (int i = 0; i < ROWS; i++) {
    for (int j = 0; j < COLS; j++) {
      cout << (bitmap[i][j] ? "1 " : "0 ");
    }
    cout << endl;
  }
}

void set_offsets(int* move, Block& block) {
  block.offset.i = 0;
  block.offset.j = 0;
  block.angle = 0;
  for (int i = 0; i < MOVE_SIZE; i++) {
    if (move[i] == 0) {
      break;
    } else if (move[i] == 1) {
      block.angle += 1;
    } else if (move[i] == 2) {
      block.offset.j -= 1;
    } else if (move[i] == 3) {
      block.offset.j += 1;
    }
  }
}

bool check(const Bitmap& bitmap, const Block& block) {
  Point point;
  for (int i = 0; i < block.num_squares; i++) {
    if (block.angle % 2) {
      point.i = block.center.i + (2 - block.angle)*block.squares[i].j;
      point.j = block.center.j - (2 - block.angle)*block.squares[i].i;
    } else {
      point.i = block.center.i + (1 - block.angle)*block.squares[i].i;
      point.j = block.center.j + (1 - block.angle)*block.squares[i].j;
    }
    point.i += block.offset.i;
    point.j += block.offset.j;
    if (point.i < 0 || point.i >= ROWS ||
        point.j < 0 || point.j >= COLS || bitmap[point.i][point.j]) {
      return false;
    }
  }
  return true;
}

void remove_rows(Bitmap& bitmap) {
  int rows_removed = 0;
  for (int i = ROWS - 1; i >= 0; i--) {
    bool full = true;
    for (int j = 0; j < COLS; j++) {
      if (!bitmap[i][j]) {
        full = false;
        break;
      }
    }
    if (full) {
      rows_removed += 1;
    } else if (rows_removed) {
      for (int j = 0; j < COLS; j++) {
        bitmap[i + rows_removed][j] = bitmap[i][j];
      }
    }
  }
  for (int i = 0; i < rows_removed; i++) {
    for (int j = 0; j < COLS; j++) {
      bitmap[i][j] = 0;
    }
  }
}

// Assumes block is initially in a valid state.
void place(const Bitmap& bitmap, Block& block, Bitmap& next_bitmap) {
  block.offset.i += 1;
  while (check(bitmap, block)) {
    block.offset.i += 1;
  }
  block.offset.i -= 1;

  for (int i = 0; i < ROWS; i++) {
    for (int j = 0; j < COLS; j++) {
      next_bitmap[i][j] = bitmap[i][j];
    }
  }

  Point point;
  for (int i = 0; i < block.num_squares; i++) {
    if (block.angle % 2) {
      point.i = block.center.i + (2 - block.angle)*block.squares[i].j;
      point.j = block.center.j - (2 - block.angle)*block.squares[i].i;
    } else {
      point.i = block.center.i + (1 - block.angle)*block.squares[i].i;
      point.j = block.center.j + (1 - block.angle)*block.squares[i].j;
    }
    point.i += block.offset.i;
    point.j += block.offset.j;
    next_bitmap[point.i][point.j] = 1;
  }

  remove_rows(next_bitmap);
}

float objective(const Bitmap& bitmap) {
  int sum_heights = 0;
  int max_height = 0;
  int sum_squared_heights = 0;
  int sum_squared_diffs = 0;

  int height = 0;
  int last_height = 0;

  for (int j = 0; j < COLS; j++) {
    for (int i = 0; i < ROWS; i++) {
      if (bitmap[i][j]) {
        height = ROWS - i - 1;
        sum_heights += height;
        if (height > max_height) {
          max_height = height;
        }
        sum_squared_heights += (height*height);
        if (j > 0) {
          sum_squared_diffs += (height-last_height)*(height-last_height);
        }
        break;
      }
    }
    last_height = height;
  }

  float var = (sum_squared_heights - (sum_heights*sum_heights)/COLS);
  return -(0.8*sum_heights + max_height + 0.15*sqrt(var) + 0.15*sum_squared_diffs);
}

float lookahead(const Bitmap& bitmap, Block* preview, int width, int depth) {
  vector<ScoredBitmap> bitmaps;
  vector<ScoredBitmap> next_bitmaps;
  bitmaps.push_back(ScoredBitmap(&bitmap, objective(bitmap)));

  for (int d = 0; d < depth; d++) {
    for (int i = 0; i < NUM_MOVES; i++) {
      set_offsets(moves[i], preview[d]);
      for (int j = 0; j < bitmaps.size(); j++) {
        if (check(*bitmaps[j].first, preview[d])) {
          Bitmap* next_bitmap = new Bitmap[1];
          place(*bitmaps[j].first, preview[d], *next_bitmap);
          next_bitmaps.push_back(ScoredBitmap(next_bitmap, objective(*next_bitmap)));
          push_heap(next_bitmaps.begin(), next_bitmaps.end(), ScoredBitmap_comp());

          if (next_bitmaps.size() > width) {
            pop_heap(next_bitmaps.begin(), next_bitmaps.end(), ScoredBitmap_comp());
            ScoredBitmap weakest_move = next_bitmaps.back();
            next_bitmaps.pop_back();
            delete[] weakest_move.first;
          }
        }
      }
    }

    while (bitmaps.size()) {
      if (d == 0) {
        bitmaps.pop_back();
        break;
      }
      ScoredBitmap old_bitmap = bitmaps.back();
      bitmaps.pop_back();
      delete[] old_bitmap.first;
    }
    while (next_bitmaps.size()) {
      ScoredBitmap new_bitmap = next_bitmaps.back();
      bitmaps.push_back(new_bitmap);
      next_bitmaps.pop_back();
    }
  }

  float score = -(1 << 30);
  while (bitmaps.size()) {
    ScoredBitmap old_bitmap = bitmaps.back();
    bitmaps.pop_back();
    if (old_bitmap.second > score) {
      score = old_bitmap.second;
    }
    delete[] old_bitmap.first;
  }
  return score;
}

int search(const Bitmap& bitmap, Block& block, Block* preview) {
  int best_move = 0;
  float best_outcome = -(1 << 30);
  int next_bitmap[ROWS][COLS];

  for (int i = 0; i < NUM_MOVES; i++) {
    set_offsets(moves[i], block);
    if (check(bitmap, block)) {
      place(bitmap, block, next_bitmap);
      float outcome = lookahead(next_bitmap, preview, 10, 3);
      if (outcome > best_outcome) {
        best_move = i;
        best_outcome = outcome;
      }
    }
  }
  return best_move;
}

void read_block(Object& raw_block, Block& block) {
  block.center.i = (int)(Number&)raw_block["center"]["i"];
  block.center.j = (int)(Number&)raw_block["center"]["j"];
  block.num_squares = 0;

  Array& offsets = raw_block["offsets"];
  for (Array::const_iterator it = offsets.Begin(); it < offsets.End(); it++) {
    block.num_squares += 1;
  }
  for (int i = 0; i < block.num_squares; i++) {
    block.squares[i].i = (Number&)offsets[i]["i"];
    block.squares[i].j = (Number&)offsets[i]["j"];
  }
}

int main(int argc, char** argv) {
  //ifstream raw_state("state.json");
  istringstream raw_state(argv[1]);
  Object state;
  Reader::Read(state, raw_state);

  int bitmap[ROWS][COLS];
  for (int i = 0; i < ROWS; i++) {
    for (int j = 0; j < COLS; j++) {
      bitmap[i][j] = ((int)(Number&)state["bitmap"][i][j] ? 1 : 0);
    }
  }

  Block block, held_block;
  read_block(state["block"], block);
  read_block(state["held_block"], held_block);

  Block preview[PREVIEW_SIZE];
  for (int i = 0; i < PREVIEW_SIZE; i++) {
    read_block(state["preview"][i], preview[i]);
  }

  int best_move = search(bitmap, block, preview);
  int* move = moves[best_move];
  for (int i = 0; i < MOVE_SIZE; i++) {
    if (move[i] == 0) {
      cout << "drop" << endl;
      break;
    } else if (move[i] == 1) {
      cout << "rotate" << endl;
    } else if (move[i] == 2) {
      cout << "left" << endl;
    } else if (move[i] == 3) {
      cout << "right" << endl;
    }
  }
}
