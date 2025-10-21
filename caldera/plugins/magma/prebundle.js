const fs = require('fs-extra');

console.log('Copying all plugin GUI source files to magma');

if (fs.existsSync('./src/plugins/')) fs.removeSync('./src/plugins/');

const plugins = fs.readdirSync('../')
plugins.forEach((plugin) => {
    // Check to see if gui directory exists
    if (!fs.existsSync(`../${plugin}/gui`)) return;

    // Copy contents of gui directory to src directory
    console.log(`Copying over "${plugin}" files...`)
    fs.copySync(`../${plugin}/gui/`, `./src/plugins/${plugin}`, { overwrite: true, recursive: true })
});

console.log('Plugin GUI source files copied!');
