var dropblox = {
  active_link: undefined,

  initialize: function() {
    $('#left-bar a').each(function() {
      var link = this.id;
      $(this).click(function() {
        dropblox.set_active_link(link);
        dropblox[link]();
        window.event.preventDefault();
      });
    });
    $('#getting_started').trigger('click');
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

  set_active_link: function(link) {
    this.active_link = link;
    $('#left-bar a').removeClass('active');
    $('#' + link).addClass('active');
  },
};
