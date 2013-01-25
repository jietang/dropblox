var board = {
  _board: undefined,
  game_id: undefined,

  initialize: function() {
    this._board = document.getElementById('board');
    this.game_id = window.location.hash.slice(1);
    this.update_interval = setInterval(this.update, 1000);
    this.start();
  },

  start: function() {
    $.ajax('start?game_id=' + this.game_id);
  },

  update: function() {
    $.ajax('game_state?game_id=' + board.game_id, {success:
      function(json) {
        if (json == 'Game not found!') {
          clearTimeout(board.update_interval);
        } else {
          board.setBoardState(json);
          if (board._board.failed()) {
            clearTimeout(board.update_interval);
          }
        }
      }
    });
  },

  setBoardState: function(json) {
    this._board.setBoardState(json);
  },
};
