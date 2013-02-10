var dropblox = {
  ANIMATE_MOVE: 40,
  WAIT_FOR_MOVE: 1000,

  games: undefined,
  cur_game: undefined,
  history_board: undefined,

  initialize: function() {
    $('#top-bar a').each(function() {
      var link = this.id;
      $(this).click(function(e) {
        if (!dropblox[link]()) {
          dropblox.set_active_link(link);
        }
        e.preventDefault();
      });
    });

    if (window.location.hash) {
      var hash = window.location.hash;
      window.location.hash = '';
      $(hash).trigger('click');
    } else if ($.cookie('active-link')) {
      $('#' + $.cookie('active-link')).trigger('click');
    } else {
      $('#getting_started').trigger('click');
    }

    if ($.cookie('team_name')) {
      this.set_team_cookie($.cookie('team_name'), $.cookie('password'));
    }
  },

  getting_started: function() {
    $('#content').html(
      '<div id=subcontent><div id="get-started-content">' +
      ' <img src="/images/logo-big.png" />' +
      ' <div class="get-started-desc">The goal of this competition is to write a ' +
      '  program that will autonomously play a Tetris variant.</div>' +
      ' <div id=get-started> ' +
      ' <a id="get-started-button" href="/dropblox_intro.html" class="bloxbutton">Get Started Here!</a>' +
      ' </div>' +
      ' <div id="instructions">' +
      '  You can try the game yourself right here! The controls are:' +
      '  <table id="instructions-table">' +
      '  <tr><td><b>Arrow keys:</b></td><td>move</td>' +
      '  <tr><td><b>Shift:</b></td><td>rotate</td>' +
      '  <tr><td><b>Space bar:</b></td><td>drop</td>' +
      '  </table>' +
      ' </div>' +
      ' <object data="Board.swf" type="application/x-shockwave-flash" width="210" height="312">' +
      '   <param name="movie" value="Board.swf" />' +
      '   <param name="flashVars" value="playable=true&squareWidth=12" />' +
      ' </object>' +
      '</div></div>'
    );
  },

  documentation: function() {
    $('#content').html(
      '<div id=subcontent>' +
      '  This is a placeholder for the documentation!' +
      '</div>'
    );
  },

  submission_history: function() {
    dropblox.games = undefined;
    dropblox.cur_game = undefined;
    $('#content').html(
      '<div id="subcontent">Loading...</div>'
    );
    $.ajax('http://127.0.0.1:9000', {
      success: function(json) {
        if ($.cookie('active-link') == 'submission_history') {
          var response = JSON.parse(json);
          if (response.code == 200) {
            dropblox.games = {};
            var left_content = '<div class="col-header">Current games</div>';
            var in_active_section = true;
            for (var i = response.games.length - 1; i >= 0; i--) {
              dropblox.games[response.games[i].id] = response.games[i];
              var game = response.games[i];
              if (in_active_section && !game.active) {
                in_active_section = false;
                if (i == response.games.length - 1) {
                  left_content += '<div class="no-games">There are no current games.</div>';
                }
                left_content += '<div class="col-header spacer">Older games</div>';
              }
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
            dropblox.history_board = dropblox.create_board('history-boards', 'history_board', 'Current Board');
            $('#leftcontent .game-link').click(function() {
              dropblox.load_game_history(this.id);
            });
            if (response.games.length) {
              setTimeout(function() {
                if (!dropblox.cur_game) {
                  dropblox.load_game_history(response.games[response.games.length - 1].id);
                }
              }, 100);
            }
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
            '<span class="code">./historyserver</span> ' +
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
      '    <param name="flashVars" value="playable=false&squareWidth=16" />' +
      '  </object>' +
      '</div>'
    );
    $('#' + target).append(html);
    return board.initialize(id);
  },

  load_game_history: function(game_id) {
    if (dropblox.cur_game && dropblox.cur_game.id != game_id) {
      $('#' + dropblox.cur_game.id).removeClass('active');
      dropblox.cur_game.states = [];
      dropblox.cur_game.index = undefined;
    }
    dropblox.cur_game = dropblox.games[game_id];
    $('#' + game_id).addClass('active');

    $('#history-message').html('Loading game data...');
    $.ajax('http://127.0.0.1:9000/details?game_id=' + game_id, {
      success: function(json) {
        if (dropblox.cur_game.id == game_id) {
          var response = JSON.parse(json);
          if (response.code == 200) {
            // Variables used to animate the game's progress in real-time.
            var index = dropblox.cur_game.index;
            var catch_up = (dropblox.cur_game.states &&
                            index === dropblox.cur_game.states.length - 1);
            var was_active = dropblox.cur_game.active;

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
            dropblox.cur_game.active = response.active;
            $('#history-message').html('Successfully loaded the game data');
            $('#post-history-boards').html(
              '<table><tr>' +
              '<td id="select-a-move">Game progress:</td>' +
              '<td><div id="move-slider"></td>' +
              '<td><button id="animate" class="bloxbutton">Animate</button></td>' +
              '</tr></table>' +
              '<div id="cur-state-label"></div>' +
              '<div class="big-spacer"><a id="copy-state" href="#">Get game state JSON for debugging</a></div>'
            );
            $('#move-slider').slider({
              min: 0,
              max: dropblox.cur_game.states.length - 1,
              step: 1,
              slide: function(event, ui) {
                dropblox.set_cur_game_state(game_id, ui.value);
              },
            });
            $('#animate').click(function(e) {
              var index = dropblox.cur_game.index;
              if (index !== undefined && index < dropblox.cur_game.states.length - 1) {
                dropblox.set_cur_game_state(game_id, index + 1);
                setTimeout(function() {
                  dropblox.animate_game(game_id, index + 1);
                }, dropblox.ANIMATE_MOVE);
              }
              e.preventDefault();
            });
            setTimeout(function() {
              $('#copy-state').zclip({
                path: 'ZeroClipboard.swf',
                copy: function() {
                  var index = dropblox.cur_game.index;
                  if (index !== undefined) {
                    return "'" + dropblox.cur_game.states[index].board + "'";
                  }
                },
              });
            }, 100);

            if (index === undefined) {
              var index = dropblox.cur_game.states.length - 1;
              dropblox.set_cur_game_state(game_id, index);
              if (dropblox.cur_game.active) {
                setTimeout(function() {
                  dropblox.animate_game(game_id, index);
                }, dropblox.ANIMATE_MOVE);
              }
            } else if (dropblox.cur_game.active && catch_up) {
              dropblox.set_cur_game_state(game_id, index);
              setTimeout(function() {
                dropblox.animate_game(game_id, index);
              }, dropblox.ANIMATE_MOVE);
            }
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

  animate_game: function(game_id, index) {
    if (this.cur_game.id == game_id && this.cur_game.index == index) {
      if (index < this.cur_game.states.length - 1) {
        this.set_cur_game_state(game_id, index + 1);
        setTimeout(function() {
          dropblox.animate_game(game_id, index + 1);
        }, dropblox.ANIMATE_MOVE);
      } else if (dropblox.cur_game.active) {
        setTimeout(function() {
          if (dropblox.cur_game.id == game_id) {
            dropblox.load_game_history(game_id);
          }
        }, dropblox.WAIT_FOR_MOVE);
      }
    }
  },

  set_cur_game_state: function(game_id, index) {
    if (dropblox.cur_game.id == game_id) {
      $('#move-slider').slider('option', 'value', index);
      dropblox.cur_game.index = index;
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
    '<div><form>' +
    ' <input type="text" id="team-name" placeholder="Team name" />' +
    ' <input type="password" id="password" placeholder="Password" />' +
    ' <button id="submit" class="bloxbutton">Submit</button>' +
    '</form></div>' +
    '<div id="login-error"></div>'
  ),

  signup_form: (
    '<div><form>' +
    ' <input type="text" id="team-name" placeholder="Team name" />' +
    ' <input type="password" id="password" placeholder="Password" />' +
    ' <input type="text" id="email1" placeholder="email1" />' +
    ' <input type="text" id="name1" placeholder="name1" />' +
    ' <input type="text" id="email2" placeholder="[optional] email2" />' +
    ' <input type="text" id="name2" placeholder="[optional] name2" />' +
    ' <input type="text" id="email3" placeholder="[optional] email3" />' +
    ' <input type="text" id="name3" placeholder="[optional] name3" />' +
    ' <button id="submit" class="bloxbutton">Submit</button>' +
    '</form></div>' +
    '<div id="login-error"></div>'
  ),

  log_in: function() {
    $('#content').html(
      '<div class="section-content"><div class="content-header">Log in</div>' + this.login_form + '</div>'
    );
    $('#team-name').focus();
    $('#submit').click(function(e) {
      dropblox.submit_login('/login', $('#team-name').val(), $('#password').val());
      e.preventDefault();
    });
  },

  sign_up: function() {
    $('#content').html(
      '<div class="section-content"><div class="content-header">Sign up</div> ' + this.signup_form + 
      "<div>Don't use any personal passwords here! You'll share one password for your " +
      "whole team, stored in a config file on each of your computers.</div>"
    );
    $('#team-name').focus();
    $('#submit').click(function(e) {
      dropblox.submit_login('/signup', $('#team-name').val(), $('#password').val(),
			   $('#email1').val(), $('#name1').val(),
			   $('#email2').val(), $('#name2').val(),
			   $('#email3').val(), $('#name3').val());
      e.preventDefault();
    });
  },

  log_out: function() {
    this.clear_team_cookie();
    return true;
  },

  submit_login: function(url, team_name, password, email1, name1, email2, name2, email3, name3) {
    this.post(url, {
      team_name: team_name,
      password: password,
      email1: email1,
      name1: name1,
      email2: email2,
      name2: name2,
      email3: email3,
      name3: name3,
    },
    function(response) {
      var verb = (url == '/login' ? 'logged in' : 'signed up');
      $('#login-error').html('Successfully ' + verb + '!');
      dropblox.set_team_cookie(team_name, password);
      setTimeout(function() {
        if (team_name == 'admin') {
          window.location.href = '/admin.html';
        } else {
          $('#' + $.cookie('last-active-link')).trigger('click');
        }
      }, 500);
    },
    function(response) {
      var data = JSON.parse(response.responseText);
      $('#login-error').html(data.message);
      dropblox.clear_team_cookie();
    });
  },

  set_team_cookie: function(team_name, password) {
    $.cookie('team_name', team_name);
    $.cookie('password', password);
    $('#login-status').html('Logged in as ' + team_name + '.');
    $('#log_in, #sign_up').addClass('hidden');
    $('#log_out').removeClass('hidden');
  },

  clear_team_cookie: function() {
    $.cookie('team_name', '');
    $.cookie('password', '');
    $('#login-status').html('Logged out.');
    $('#log_in, #sign_up').removeClass('hidden');
    $('#log_out').addClass('hidden');
  },

  set_active_link: function(link) {
    $.cookie('active-link', link);
    if (link != 'log_in' && link != 'sign_up') {
      $.cookie('last-active-link', link);
    }
    $('#left-bar a, #top-bar a').removeClass('active');
    $('#' + link).addClass('active');
  },

  format_timestamp: function(ts) {
    var date = new Date(1000*ts);
    var hours = date.getHours();
    var am_pm;
    if (hours < 12) {
	am_pm = ' AM';
    } else {
	am_pm = ' PM';
	hours -= 12
    }
    if (hours === 0) {
	hours += 12
    }
    return (hours +
            (date.getMinutes() < 10 ? ':0' : ':') + date.getMinutes() +
            (date.getSeconds() < 10 ? ':0' : ':') + date.getSeconds() +
	    am_pm)
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
