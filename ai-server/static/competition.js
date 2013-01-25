var competition = {
  boards: {},

  initialize: function() {
    $.ajax('/competition_state', {
      success: function(json) {
        var data = JSON.parse(json);
        for (var team in data.boards) {
          $('#boards').append('<div id="' + team + '-container"></div>');
          competition.boards[team] = competition.create_board(team + '-container', team, team);
          competition.boards[team].setBoardState(data.boards[team]);
        }
        setInterval(competition.update, 1000);
      },
      error: function(json) {
        var data = JSON.parse(json);
        $('#boards').html(data.message);
      },
    });
  },

  create_board: function(target, id, header) {
    var html = (
      '<div class="container">' +
      '  <div class="header">' + header + '</div>' +
      '  <object id="' + id + '" data="Board.swf" type="application/x-shockwave-flash" width="175" height="260">' +
      '    <param name="movie" value="Board.swf" />' +
      '    <param name="flashVars" value="squareWidth=10" />' +
      '  </object>' +
      '</div>'
    );
    $('#' + target).append(html);
    return board.initialize(id);
  },

  update: function() {
    $.ajax('/competition_state', {
      success: function(json) {
        var data = JSON.parse(json);
        for (var team in data.boards) {
          competition.boards[team].setBoardState(data.boards[team]);
        }
      },
      error: function(json) {
        var data = JSON.parse(json);
        console.log('Error in update:', data.message);
      },
    });
  },
};
