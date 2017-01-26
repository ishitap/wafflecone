import moment from 'moment';

function display(task) {
  if (task.custom_display && task.custom_display != "") 
    return task.custom_display
  else if (task.label_index > 0)
    return task.label + "-" + task.label_index
  else
    return task.label
}


function getAttributesToColumnNumbers(attributes) {
	var cols = {}
	attributes.map(function (a, i) {
		cols[a.id] = i
	})
	return cols
}

function taskAsRow(process,task, cols) {
	var arr = [display(task), '' + task.inputs.length, '' + task.items.length, '' + moment(task.created_at).format("MM/DD/YYYY")]
	
	var attrArray = Array(process.attributes.length).fill('')
	
	task.attribute_values.map(function (av) {
		var col = cols[av.attribute]
		attrArray[col] = av.value.replace(/"/g, '""');
	})

	arr = arr.concat(attrArray)

	return '"' + arr.join('","') + '"'
}

function toCSV(process, tasks) {

	var attributeColumns = getAttributesToColumnNumbers(process.attributes)

	var arr = ['Task', 'Inputs', 'Outputs', 'Date Created']
	var attrArr = process.attributes.map(function (a) { return a.name.replace(/"/g, '""') })

	var firstRow = [ '"' + arr.concat(attrArr).join('","') + '"']

	var tasksAsRows = tasks.map(function (task) {
		return taskAsRow(process,task, attributeColumns)
	})

	var csv = tasksAsRows.join('\n')

	return firstRow + '\n' + csv

}

export { display, getAttributesToColumnNumbers, toCSV }