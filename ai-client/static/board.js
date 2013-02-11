var board = {
  initialize: function(id) {
    var result = {
      _board: document.getElementById(id),
    };
    result.start = this._start;
    result.update = this._update;
    result.setBoardState = this._setBoardState;
    result.issueCommand = this._issueCommand;
    result.draw = this._draw;
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

  _setBoardState: function(json, skip_draw) {
    this._board.setBoardState(json);
    if (!skip_draw) {
      this._board.draw();
    }
  },

  _issueCommand: function(command, skip_draw) {
    this._board.issueCommand(command);
    if (!skip_draw) {
      this._board.draw();
    }
  },

  _draw: function() {
    this._board.draw();
  },
};
