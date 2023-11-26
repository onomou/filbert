
const initialValues = {};

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
    if(event.target.type == "checkbox") {
      newValue = event.target.checked;
    } else if(event.target.type == "select-one" || event.target.type == "select-multiple"){
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
      // Input value has changed from its initial value
      // console.log(`Input with ID ${input.id} has changed.`);
      theParent.classList.add("changed")
      // Perform actions when the input value changes
    } else {
      // console.log(`Input with ID ${input.id} is unchanged.`);
      theParent.classList.remove("changed")
    }
  }