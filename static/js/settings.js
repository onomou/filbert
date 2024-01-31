$(document).ready(function () {
    
    $("#section-selection").on("change", function() {
    // console.log("target")
    var target = $(this).val();
    var valid_ids = $("#hidden > div").map(function() {return this.id}).get()
    var selected_options = $("#hidden").find('div[data-section="' + target + '"]');
    // if (valid_ids.includes(target)) {
    if (selected_options.length > 0) {
        $("#section-settings").html(selected_options.html())
        // var selected_options = $("#" + target)
        // console.log(target)
        // console.log(selected_options)
    } else {
        create_new_section()
    }
  });
    $("#section-selection").trigger("change");
    var max_size = Math.min(8, $("#section-selection option").length)
    $("#section-selection").prop("size",max_size)
})

function create_new_section() {
    var selected_options = $("#new-section")
    $("#section-settings").html(selected_options.html())
}
