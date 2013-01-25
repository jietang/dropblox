var dropblox = {
  games: undefined,
  cur_game: undefined,

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
              '<div id="rightcontent">Click on a game to review your AI\'s moves.</div>'
            );
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
            '<div class="spaced">You can start this server by running ' +
            '<span class="code">python history.py</span> ' +
            'in your ai-client folder.</div>'
          );
        }
      },
    });
  },

  load_game_history: function(game_id) {
    dropblox.cur_game = dropblox.games[game_id];
    $('#' + game_id).addClass('active');
    $('#rightcontent').html('Loading game data...');
    $.ajax('http://localhost:9000/details?game_id=' + game_id, {
      success: function(json) {
        if (dropblox.cur_game.id == game_id) {
          var response = JSON.parse(json);
          if (response.code == 200) {
            $('#rightcontent').html('Successfully loaded the game data.');
            console.log(response);
          } else {
            $('#rightcontent').html(response.error);
          }
        }
      },
      error: function() {
        if (dropblox.cur_game.id == game_id) {
          $('#rightcontent').html('There was an error loading the game data.');
        }
      },
    });
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
