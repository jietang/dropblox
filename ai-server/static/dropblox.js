var board = {
  _board: undefined,

  initialize: function() {
    this._board = document.getElementById('board');
  },

  update: function(json) {
    this._board.setBoardState(json);
  },
};
