from RawBlockData import raw_block_data

COLS = 12
#ROWS = 33
ROWS = 33
MAX_BLOCK_SIZE = 10

types = []
blocks = []

def loadBlockData():
  types.extend(raw_block_data[0][1:])
  if len(types) != raw_block_data[0][0]:
    print "Read an incorrect number of difficulty levels."

  for i in range(1, types[-1] + 1):
    data = raw_block_data[i]
    blocks.append({
      'type': i - 1,
      'center': {
        'i': data[1],
        'j': data[0],
      },
      'offsets': [{
        'i': data[2*j + 4],
        'j': data[2*j + 3],
      } for j in range(data[2])],
    })

  for block in blocks:
    block['center']['i'] += MAX_BLOCK_SIZE - height(block)
    block['center']['j'] += COLS/2

def height(block):
  return (max(offset['i'] for offset in block['offsets'])
          - min(offset['i'] for offset in block['offsets']) + 1)

loadBlockData()
