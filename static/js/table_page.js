var rows, columns, table, data
var options = {
    enableCellNavigation: true,
    enableColumnReorder: false,
    editable: true,
    enableSorting: true,
    // Configure other SlickGrid options
};
// console.log(users_data_url)
// var 
//Define variables for input elements
var fieldEl = document.getElementById("filter-field");
var typeEl = document.getElementById("filter-type");
var valueEl = document.getElementById("filter-value");

$(document).ready(function () {
    let table; // Define table outside the function

    fetch(data_url)
        .then(response => response.json())
        .then(data => {
            rows = data['rows'];
            // columns = data['columns'];
            // table = new Slick.Grid("#main-grid", rows, columns, options);
            //initialize table
            table = new Tabulator("#main-grid", {
                data: rows, // assign data to table
                // responsiveLayout: "hide",  // hide columns that don't fit on the table
                movableColumns: true,      // allow column order to be changed
                // layout: "fitColumns",
                autoColumns: true, // create columns from data field names
            });
            table.on('tableBuilt', function() {
                console.log(table.getColumns());
                table.getColumns().forEach(function(column) {
                    fieldEl.add(new Option(column._column.field));
                    console.log('added column: ', column._column.field);
                });
            })
        })
        .catch(error => console.log(error));
});


//Custom filter example
function customFilter(data){
    return data.car && data.rating < 3;
}

//Trigger setFilter function with correct parameters
function updateFilter(){
  var filterVal = fieldEl.options[fieldEl.selectedIndex].value;
  var typeVal = typeEl.options[typeEl.selectedIndex].value;

  var filter = filterVal == "function" ? customFilter : filterVal;

  if(filterVal == "function" ){
    typeEl.disabled = true;
    valueEl.disabled = true;
  }else{
    typeEl.disabled = false;
    valueEl.disabled = false;
  }

  if(filterVal){
    table.setFilter(filter,typeVal, valueEl.value);
  }
}

//Update filters on value change
document.getElementById("filter-field").addEventListener("change", updateFilter);
document.getElementById("filter-type").addEventListener("change", updateFilter);
document.getElementById("filter-value").addEventListener("keyup", updateFilter);

//Clear filters on "Clear Filters" button click
document.getElementById("filter-clear").addEventListener("click", function(){
  fieldEl.value = "";
  typeEl.value = "=";
  valueEl.value = "";

  table.clearFilter();
});