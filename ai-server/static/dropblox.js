var dropblox = {
  games: undefined,
  cur_game: undefined,
  history_board: undefined,

  initialize: function() {
    $('#left-bar a, #top-bar a').each(function() {
      var link = this.id;
      $(this).click(function() {
        dropblox.set_active_link(link);
        dropblox[link]();
        window.event.preventDefault();
      });
    });
    if ($.cookie('active-link')) {
      $('#' + $.cookie('active-link')).trigger('click');
    } else {
      $('#getting_started').trigger('click');
    }
  },

  getting_started: function() {
    $('#content').html(
      '<div>' +
      '  This is a placeholder for the getting started page!' +
      '</div>'
    );
  },

  documentation: function() {
    $('#content').html(
      '<div>' +
      '  This is a placeholder for the documentation!' +
      '</div>'
    );
  },

  submission_history: function() {
    $('#content').html(
      '<h3>Submission history</h3>' +
      '<div id="subcontent">Loading...</div>'
    );
    $.ajax('http://localhost:9000', {
      success: function(json) {
        if ($.cookie('active-link') == 'submission_history') {
          var response = JSON.parse(json);
          if (response.code == 200) {
            dropblox.games = {};
            var left_content = '';
            for (var i = response.games.length - 1; i >= 0; i--) {
              dropblox.games[response.games[i].id] = response.games[i];
              var game = response.games[i];
              var date_str = dropblox.format_timestamp(game.timestamp);
              left_content += '<div id="' + game.id + '" class="game-link">';
              left_content += 'Game ' + i + ' (' + date_str + ')</div>';
            }
            $('#subcontent').html(
              '<div id="leftcontent">' + left_content + '</div>' +
              '<div id="rightcontent">' + 
              '  <div id="history-message">Click on a game to review your AI\'s moves.</div>' +
              '  <div id="history-boards"></div>' +
              '  <div id="post-history-boards"></div>' +
              '</div>'
            );
            dropblox.history_board = dropblox.create_board('history-boards', 'history_board', 'Board at this turn:');
            $('#leftcontent .game-link').click(function() {
              dropblox.load_game_history(this.id);
            });
          } else {
            $('#subcontent').html(response.error);
          }
        }
      },
      error: function() {
        if ($.cookie('active-link') == 'submission_history') {
          $('#subcontent').html(
            '<div>Request failed! Make sure your history server is running.</div>' +
            '<div class="spacer">You can start this server by running ' +
            '<span class="code">python history.py</span> ' +
            'in your ai-client folder.</div>'
          );
        }
      },
    });
  },

  create_board: function(target, id, header) {
    var html = (
      '<div class="container">' +
      '  <div class="header">' + header + '</div>' +
      '  <object id="' + id + '" data="Board.swf" type="application/x-shockwave-flash" width="280" height="416">' +
      '    <param name="movie" value="Board.swf" />' +
      '  </object>' +
      '</div>'
    );
    $('#' + target).append(html);
    b = board.initialize(id);
    return b;
  },

  load_game_history: function(game_id) {
    dropblox.cur_game = dropblox.games[game_id];
    $('#' + game_id).addClass('active');
    $('#history-message').html('Loading game data...');
    $.ajax('http://localhost:9000/details?game_id=' + game_id, {
      success: function(json) {
        if (dropblox.cur_game.id == game_id) {
          var response = JSON.parse(json);
          if (response.code == 200) {
            dropblox.cur_game.states = [];
            for (var i = 0; i < response.states.length; i++) {
              var moves = JSON.parse(response.states[i].moves);
              for (var j = 0; j < moves.length + 1; j++) {
                var state = {
                  state_index: i,
                  move_index: j,
                  board: response.states[i].state,
                  moves: [],
                }
                for (var k = 0; k < j; k++) {
                  state.moves.push(moves[k]);
                }
                dropblox.cur_game.states.push(state);
              }
            }
            $('#history-message').html('Successfully loaded the game data');
            $('#post-history-boards').html(
              '<table><tr>' + 
              '<td id="select-a-move">Game progress:</td>' +
              '<td><div id="move-slider"></td>' +
              '</tr></table>' +
              '<div id="cur-state-label"></div>'
            );
            $('#move-slider').slider({
              min: 0,
              max: dropblox.cur_game.states.length - 1,
              step: 1,
              slide: function(event, ui) {
                dropblox.set_cur_game_state(game_id, ui.value);
              },
            });
            dropblox.set_cur_game_state(game_id, 0);
          } else {
            $('#history-message').html(response.error);
          }
        }
      },
      error: function() {
        if (dropblox.cur_game.id == game_id) {
          $('#history-message').html('There was an error loading the game data.');
        }
      },
    });
  },

  set_cur_game_state: function(game_id, index) {
    if (dropblox.cur_game.id == game_id) {
      var state = dropblox.cur_game.states[index];
      $('#cur-state-label').html('Turn ' + state.state_index + ', moves: [' + state.moves.join(', ') + ']');
      dropblox.history_board.setBoardState(state.board, true);
      for (var i = 0; i < state.moves.length; i++) {
        dropblox.history_board.issueCommand(state.moves[i], true);
      }
      dropblox.history_board.draw();
    }
  },

  login_form: (
    '<form><fieldset><table>' +
    ' <tr><td>Team name:</td><td><input type="text" id="team-name"></td>' +
    ' <tr><td>Password:</td><td><input type="password" id="password"></td>' +
    ' <tr><td><button id="submit">Submit</button></td>' +
    '</table></fieldset></form>'
  ),

  log_in: function() {
    $('#content').html(
      '<h3>Log in</h3>' + this.login_form
    );
    $('#submit').click(function() {
      dropblox.submit_login('log_in', $('#team-name').val(), $('#password').val());
      window.event.preventdefault();
    });
  },

  sign_up: function() {
    $('#content').html(
      '<div><h3>Sign up</h3> ' + this.login_form + '</div>'
    );
    $('#submit').click(function() {
      dropblox.submit_login('sign_up', $('#team-name').val(), $('#password').val());
      window.event.preventdefault();
    });
  },

  submit_login: function(type, team_name, password) {
    console.debug(type, team_name, password);
  },

  set_active_link: function(link) {
    $.cookie('active-link', link);
    $('#left-bar a, #top-bar a').removeClass('active');
    $('#' + link).addClass('active');
  },

  format_timestamp: function(ts) {
    var date = new Date(1000*ts);
    return (date.getHours() +
            (date.getMinutes() < 10 ? ':0' : ':') + date.getMinutes() +
            (date.getSeconds() < 10 ? ':0' : ':') + date.getSeconds())
  },
};
