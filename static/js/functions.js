
const initialValues = {};

function initTinyMCE() {
  try {tinymce.activeEditor.remove("#description");}
  catch {};
  tinymce.init({
    selector: '#description',
    menubar: false,
    toolbar_location: 'bottom',
    toolbar_mode: 'wrap',
    toolbar: [
      { name: 'history', items: [ 'undo', 'redo' ] },
      { name: 'styles', items: [ 'styles', 'numlist', 'bullist', 'link' ] },
      { name: 'formatting', items: [ 'bold', 'italic' ] },
      { name: 'alignment', items: [ 'alignleft', 'aligncenter', 'alignright', 'alignjustify' ] },
      { name: 'indentation', items: [ 'outdent', 'indent' ] },
      { name: 'extra', items: ['code']}
    ],
    plugins: 'lists autolink link quickbars',
    automatic_uploads: true,
    images_upload_url: '/upload_image',
    default_link_target: '_blank',
    link_default_protocol: 'https',
    apply_source_formatting: true,
    indent: false, // fixes \n issue: https://stackoverflow.com/a/39489073
    // width: 650,
    width: '100%',
    height: 260,
    setup: (editor) => {
      editor.on('init', (event) => {
        tinyMCE.get("description").setContent(document.getElementById("raw-description").innerHTML)
        initialValues['description'] = tinyMCE.get("description").getContent()
      })
    },
    init_instance_callback: function(editor) {
      editor.on('NodeChange', handleDescriptionChange)
    }
  });
}

function initDatePicker() {
  $("#due_at").datetimepicker({
    format: "Y-m-d H:i",
    timepicker: true,
    //inline: true,
    showButtonPanel: true,
    controlType: "select",
    // minDate: '0',
    disableWeekDays: [6],
    defaultDate: '+1970/01/02',
    allowTimes: default_times,
  });

  $('#due_at').on('change.datetimepicker', handleInputChange);
}

function requiredFieldsValid() {
  var form = $(this).closest('form');
  var formValid = true;
  $("form").each(function() {
    // Check if all required fields within the form are filled in
    var valid = true;
    $(this).find(':input[required]').each(function() {
      if ($(this).val() === '') {
        valid = false;
          return false;
      }
    });
    formValid = valid;
  })
  return formValid; // Exit the loop early if any required field is empty
}

function initAssignmentDetails() {

  // Prevent accidental changes to assignment name
  $('#name-box').on('input', function() {
    if ($("#new-assignment-header").length == 0) {
      if ($(this).hasClass('changed')) {
        $('#submit-button').addClass('disabled');
        $('#submit-button').attr('title', 'Click again to enable');
      } else {
          $('#submit-button').removeClass('disabled');
          $('#submit-button').removeAttr('title');
      }
    }
  });

  $('#submit-button').on('click', function() {
      if ($(this).hasClass('disabled')) {
          // Handle click on disabled button here
          $(this).removeClass('disabled');
          return false;
      } else {
        // $("#assignment-details-wrapper").addClass('disable-overlay')
        if (requiredFieldsValid()) {
          $(".disable-overlay").text('Saving')
          $(".disable-overlay").css('display', 'flex')
        }
        return true;
      }
  });

  $('.additional-actions button').each(function() {
    $(this).on('click', function() {
      if (requiredFieldsValid()) {
        $(".disable-overlay").text('Please wait')
        $(".disable-overlay").css('display', 'flex')
      }
    });
  });
  
  // Validate points field to allow only nonnegative integers
  $("#points_possible").on("input", function () {
    this.value = this.value.replace(/[^0-9]/g, '');
    if (this.value < 0) {
      this.value = '';
    }
  });
  
  $(".additional-actions button").each(function() {
    $(this).prop('disabled', $("#assignment-details-wrapper").data("assignmentid") == 0)
  })

  // highlight current assignment
  $(".assignment.sidebar-item.active").removeClass("active")
  $("#"+$("#assignment-details-wrapper").data("assignmentid")).addClass('active')
}

function initChangeHandler() {
  document.querySelectorAll('input').forEach(input => {
    // Gather initial values
    if(input.type == "checkbox") {
      initialValues[input.id] = input.checked
    } else {
      initialValues[input.id] = input.value;
    }
    // Add event listeners to input elements
    input.addEventListener('input', handleInputChange);
  });
  document.querySelectorAll('select').forEach(input => {
    // Gather initial values
    initialValues[input.id] = [...input.selectedOptions].map(x => x.value);
    // Add event listeners to input elements
    input.addEventListener('change', handleInputChange);
  });
  
// handle file drag and drop for assignment attachment
    $("#assignment-attachment").change(function() {
      if(this.files.length > 0) {
          $(this).addClass('file-present')
          $(this).parent().parent().addClass('changed')
          $("#assignment-attachment-status").text(this.files[0].name)
          console.log("File")
      } else {
          $(this).removeClass('file-present')
          $(this).parent().parent().removeClass('changed')
          $("#assignment-attachment-status").text("Drop a file here")
          console.log("No file")
      }
    })

    // Scroll to show selected assignment
    const selectedAssignment = document.querySelector(".secondary-sidebar .item.active")

    if (selectedAssignment) {
      selectedAssignment.scrollIntoView({
        behavior: "smooth", // Use "smooth" for smooth scrolling, or "auto" for instant scrolling
        block: "nearest",   // Scroll block: "start", "center", "end", or "nearest"
        inline: "nearest"   // Scroll inline: "start", "center", "end", or "nearest"
      });
    }

  // enable external tool box if external tool is selected
  var submission_types_element = document.getElementById("submission-types")
  submission_types_element.addEventListener('change', function(event) {
    //  document.getElementById("url").disabled = !([...event.target.selectedOptions].map(x => x.value).includes('external_tool'))
    document.querySelectorAll(".external-tool-options").forEach(x => {
      x.disabled = !([...event.target.selectedOptions].map(y => y.value).includes('external_tool'))
      // x.style.display = !([...event.target.selectedOptions].map(y => y.value).includes('external_tool'))
    })
  });
  // submission_types_element.dispatchEvent(new CustomEvent('change', {'target': {'selectedOptions': submission_types_element.selectedOptions}}))
  submission_types_element.dispatchEvent(new CustomEvent('change', {}))
}

function isValidDate(dateString) {
  const regex = /^\d{4}-\d{2}-\d{2}$/; // YYYY-MM-DD format
  return regex.test(dateString);
}

function valuesEqual(value1, value2) {
  // Handle numeric equivalence (1.0 == 1)
  if (typeof value1 === 'number' && typeof value2 === 'number') {
    return parseFloat(value1) === parseFloat(value2);
  }
  // Handle arrays
  if (JSON.stringify(value1) == JSON.stringify(value2)) {
    return true;
  }
  // Handle date format equivalence ("2023-10-30" == "10/30/2023")
  if (isValidDate(value1) && isValidDate(value2)) {
    const date1 = new Date(value1);
    const date2 = new Date(value2);
    return date1.getTime() === date2.getTime();
  }
  // Handle boolean equivalence (True == true == 1 == yes)
  // if (typeof value1 === 'boolean' && typeof value2 === 'boolean') {
  //     return parseFloat(value1) === parseFloat(value2); // TODO: this
  // }
  // Handle other cases (string equivalence, etc.)
  return value1 === value2;
}

function handleInputChange(event) {
  // console.log("another input handled")
  var newValue;
  if (event.target.type == "checkbox") {
    newValue = event.target.checked;
  } else if (event.target.type == "select-one" || event.target.type == "select-multiple") {
    newValue = [...event.target.selectedOptions].map(x => x.value)
  } else {
    newValue = event.target.value;
  }
  var oldValue = initialValues[event.target.id]
  // const oldValue = event.target.dataset.initialValue; // Store initial value as a data attribute
  theParent = document.getElementById(event.target.id).parentElement

  if (!valuesEqual(newValue, oldValue)) {
    // React to input changes
    console.log('Input Value Changed: old: ', newValue);
    console.log('Input Value Changed: new: ', newValue);
    // }
    // if (input.value !== initialValues[event.target.id]) {
    // Input value has changed from its initial value
    // console.log(`Input with ID ${input.id} has changed.`);
    theParent.classList.add("changed")
    // Perform actions when the input value changes
  } else {
    // console.log(`Input with ID ${input.id} is unchanged.`);
    theParent.classList.remove("changed")
  }
}

// handle tinyMCE separately
function handleDescriptionChange(event) {
  // console.log("description handled")
  var newValue = tinyMCE.get("description").getContent()
  var oldValue = initialValues["description"]
  // const oldValue = event.target.dataset.initialValue; // Store initial value as a data attribute
  theParent = document.getElementById("description").parentElement

  if (!valuesEqual(newValue, oldValue)) {
    // React to input changes
    console.log('Input Value Changed: old: ', newValue);
    console.log('Input Value Changed: new: ', newValue);
    // }
    // if (input.value !== initialValues[event.target.id]) {
    // console.log(`Input with ID ${input.id} has changed.`);
    theParent.classList.add("changed")
    // Perform actions when the input value changes
  } else {
    // console.log(`Input with ID ${input.id} is unchanged.`);
    theParent.classList.remove("changed")
  }
}



function loadPage(data_url, history_url) {
  if (data_url != history_url) {
    window.history.pushState(null,"",history_url);
  }
  fetch(data_url)
    .then(response => {return response.text()})
    .then(data => {
      var details = document.getElementById('assignment-details')
      if (data) {
        details.innerHTML = data
      } else {
        details.innerHTML = ""
      }
    })
    .then(() => {
      // reinit interactive elements
      $("#assignment-details").data("assignmentid", )
      initTinyMCE();
      initDatePicker();
      initChangeHandler();
      initAssignmentDetails();
    }).then(() => {console.log("DONE!")});
}

// silent reload page
function reloadPage() {
    // var data_url = $('#'+elementId).data('dataurl');
    var data_url = $('#assignment-details').data('dataurl');
    loadPage(data_url, data_url);
    // var history_url = $(this).attr('href');
    // window.history.pushState(null,"",history_url);
    // fetch(data_url)
    // .then(response => {return response.text()})
    // .then(data => {
    //   var details = document.getElementById('assignment-details')
    //   if (data) {
    //     details.innerHTML = data
    //   } else {
    //     details.innerHTML = ""
    //   }
    // })
    // .then(() => {
    //   // reinit interactive elements
    //   initTinyMCE();
    //   initDatePicker();
    //   initChangeHandler();
    // });
    // event.preventDefault();
    return false;
}
