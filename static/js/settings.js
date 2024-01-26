$(document).ready(function () {
$("#section-selection").on('change', function() {
    console.log('target')
    var target = $(this).val();
    var selected_options = $("#" + target)
    console.log(target)
    console.log(selected_options)
    $("#section-settings").html(selected_options.html())
  });
  $(document).ready(function(){
      $('.section-selection').trigger('change');
  });
})