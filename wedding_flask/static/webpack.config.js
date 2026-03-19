const path = require('path');
const { CleanWebpackPlugin } = require('clean-webpack-plugin');

module.exports = {
    mode: 'development', // or 'production' for minified output
    entry: './ts/maps.ts', // your main TS entry
    devtool: 'source-map',
    module: {
        rules: [
            {
                test: /\.ts$/,
                use: 'ts-loader',
                exclude: /node_modules/
            }
        ]
    },
    resolve: {
        extensions: ['.ts', '.js']
    },
    output: {
        filename: 'maps.bundle.js',   // compiled output
        path: path.resolve(__dirname, 'js') // ./static/js/
    },
    plugins: [new CleanWebpackPlugin()]
};