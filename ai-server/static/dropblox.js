var dropblox = {
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
      '<div>' +
      '  This is a placeholder for the submission history!' +
      '</div>'
    );
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
      '<div><h3>Log in:</h3> ' + this.login_form + '</div>'
    );
    $('#submit').click(function() {
      dropblox.submit_login('log_in', $('#team-name').val(), $('#password').val());
      window.event.preventdefault();
    });
  },

  sign_up: function() {
    $('#content').html(
      '<div><h3>Sign up:</h3> ' + this.login_form + '</div>'
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
};
