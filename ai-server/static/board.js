var board = {
  initialize: function(id) {
    var result = {
      _board: document.getElementById(id),
    };
    result.start = this._start;
    result.update = this._update;
    result.setBoardState = this._setBoardState;
    return result;
  },

  _start: function(game_id) {
    this.game_id = game_id;
    $.ajax('start?game_id=' + game_id);
    this.update_interval = setInterval(this.update, 1000);
  },

  _update: function() {
    $.ajax('game_state?game_id=' + board.game_id, {success:
      function(elt) {
        return function(json) {
          if (json == 'Game not found!') {
            clearTimeout(elt.update_interval);
          } else {
            elt.setBoardState(json);
            if (elt._board.failed()) {
              clearTimeout(elt.update_interval);
            }
          }
        }
      } (this)
    });
  },

  _setBoardState: function(json) {
    this._board.setBoardState(json);
  },
};
