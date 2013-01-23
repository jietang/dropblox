from copy import deepcopy

COLS = 12
ROWS = 33

class InvalidMoveError(ValueError):
  pass

class Helper(object):
  # Takes a bitmap and a block and returns True if the block is in a valid
  # position on that bitmap. The block could be an invalid position because:
  #   a) it could be off the edges of the board, or
  #   b) one of its squares could be occupied.
  @staticmethod
  def check(bitmap, block):
    for point in block['offsets']:
      i = point['i'] + block['center']['i']
      j = point['j'] + block['center']['j']
      if i < 0 or i >= ROWS or j < 0 or j >= COLS or bitmap[i][j]:
        return False
    return True

  # Movement logic follows! All of these methods take a bitmap and a block.
  # They return the block obtained by performing that move on the board.
  # The original block is not modified.
  #
  # If the move is not legal, these methods throw an InvalidMoveError.
  # The block's original position is assumed to be valid.
  @staticmethod
  def rotate(bitmap, block):
    result = deepcopy(block)
    result['offsets'] = [{
      'i': offset['j'],
      'j': -offset['i'],
    } for offset in result['offsets']]
    if not Helper.check(bitmap, result):
      raise InvalidMoveError()
    return result

  @staticmethod
  def translate(bitmap, block, i=0, j=0):
    result = deepcopy(block)
    result['center'] = {
      'i': result['center']['i'] + i,
      'j': result['center']['j'] + j,
    }
    if not Helper.check(bitmap, result):
      raise InvalidMoveError()
    return result

  @staticmethod
  def left(bitmap, block):
    return Helper.translate(bitmap, block, j=-1)

  @staticmethod
  def right(bitmap, block):
    return Helper.translate(bitmap, block, j=1)

  @staticmethod
  def up(bitmap, block):
    return Helper.translate(bitmap, block, i=-1)

  @staticmethod
  def down(bitmap, block):
    return Helper.translate(bitmap, block, i=1)

  # Returns the number of rows that this block would drop if dropped.
  # If the block is not in a valid position, returns -1.
  @staticmethod
  def rows_free(bitmap, block):
    temp_block = deepcopy(block)
    while Helper.check(bitmap, temp_block):
      temp_block['center']['i'] += 1
    return temp_block['center']['i'] - block['center']['i'] - 1

  # Takes a bitmap and a block. Drops that block as far as possible, then
  # removes any rows that are now full. Returns a dict:
  # {
  #   'bitmap': The new bitmap after the drop.
  #   'num_rows_cleared': The number of rows cleared by the drop.
  #   'delta_score': The number of points scored by this drop.
  # }
  # If the original block's position is invalid, throws an InvalidMoveError.
  @staticmethod
  def drop(bitmap, block):
    new_bitmap = deepcopy(bitmap)
    rows_free = Helper.rows_free(bitmap, block)
    if rows_free < 0:
      raise InvalidMoveError()
    for point in block['offsets']:
      i = point['i'] + block['center']['i'] + rows_free
      j = point['j'] + block['center']['j']
      new_bitmap[i][j] = block['type'] + 1
    return Helper.remove_rows(new_bitmap)

  # Takes a bitmap and removes any full rows. Returns the same data as drop().
  @staticmethod
  def remove_rows(bitmap):
    new_bitmap = [row for row in bitmap if not all(row)]
    num_rows_cleared = ROWS - len(new_bitmap)
    new_bitmap = [[0 for j in range(COLS)] for i in range(num_rows_cleared)] + new_bitmap
    return {
      'bitmap': new_bitmap,
      'num_rows_cleared': num_rows_cleared,
      'delta_score': 2**num_rows_cleared - 1,
    }
