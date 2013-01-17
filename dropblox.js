var board = {
  _board: undefined,

  initialize: function() {
    this._board = document.getElementById('board');
  },

  getBoardState: function() {
    return JSON.parse(this._board.getBoardState());
  },

  getCurBlock: function() {
    return JSON.parse(this._board.getCurBlock());
  },

  getHeldBlock: function() {
    return JSON.parse(this._board.getHeldBlock());
  },

  getNextBlocks: function() {
    return JSON.parse(this._board.getNextBlocks());
  },
};
