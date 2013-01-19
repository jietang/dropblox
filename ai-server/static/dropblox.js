var board = {
  _board: undefined,

  initialize: function() {
    this._board = document.getElementById('board');
  },

  getBoardState: function() {
    return JSON.parse(this._board.getBoardState());
  },

  issueCommand: function(command) {
    this._board.issueCommand(command);
  },

  rotate: function() {
    this.issueCommand(0);
  },

  left: function() {
    this.issueCommand(3);
  },

  right: function() {
    this.issueCommand(1);
  },

  down: function() {
    this.issueCommand(2);
  },

  hard_drop: function() {
    this.issueCommand(4);
  },

  swap: function() {
    this.issueCommand(5);
  },
};
