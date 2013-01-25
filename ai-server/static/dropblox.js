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

  log_in: function() {
    $('#content').html(
      '<div>' +
      '  This is a placeholder for the login page!' +
      '</div>'
    );
  },

  sign_up: function() {
    $('#content').html(
      '<div>' +
      '  This is a placeholder for the signup page!' +
      '</div>'
    );
  },

  set_active_link: function(link) {
    $.cookie('active-link', link);
    $('#left-bar a, #top-bar a').removeClass('active');
    $('#' + link).addClass('active');
  },
};
