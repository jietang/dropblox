var competition = {
  boards: {},

  initialize: function() {
    this.post('/competition_state',
      {
        team_name: $.cookie('team_name'),
        password: $.cookie('password'),
      },
      function(json) {
        var data = JSON.parse(json);
        var empty = true;
        for (var team in data.boards) {
          $('#boards').append('<div id="' + team + '-container"></div>');
          competition.boards[team] = competition.create_board(team + '-container', team, team);
          competition.boards[team].setBoardState(data.boards[team]);
          empty = false;
        }
        if (empty) {
          $('#boards').html('No competition is currently running.');
        } else {
          setInterval(competition.update, 1000);
        }
      },
      function(data) {
        $('#boards').html(data);
      }
    );
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
    this.post('/competition_state',
      {
        team_name: $.cookie('team_name'),
        password: $.cookie('password'),
      },
      function(json) {
        var data = JSON.parse(json);
        for (var team in data.boards) {
          competition.boards[team].setBoardState(data.boards[team]);
        }
      }
    );
  },


  post: function(url, data, success, error) {
    $.ajax({
      type: 'POST',
      url: url,
      data: JSON.stringify(data),
      contentType: "application/json",
      dataType: "json",
      success: success,
      error: error,
    });
  },
};
