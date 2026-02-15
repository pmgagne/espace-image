module.exports = {
    env: {
        browser: true,
        es6: true,
    },
    extends: [
        'eslint:recommended',
    ],
    parserOptions: {
        ecmaVersion: 2015,
        sourceType: 'script',
    },
    plugins: ['compat', 'html'],
    rules: {
        'no-console': 'warn',
        'no-unused-vars': ['warn', { argsIgnorePattern: '^_' }],
        'compat/compat': 'error',
    },
    overrides: [
        // Legacy code (iPad 2 / iOS 9.3.5) - ES5 only
        {
            files: [
                'app/templates/legacy/**/*.html',
                'app/static/js/legacy.js',
            ],
            parserOptions: {
                ecmaVersion: 5,
            },
            env: {
                browser: true,
                es6: false,
            },
            rules: {
                'no-var': 'off',
                'prefer-arrow-callback': 'off',
                'prefer-const': 'off',
                'object-shorthand': 'off',
                'prefer-template': 'off',
                'no-restricted-syntax': [
                    'error',
                    {
                        selector: 'ArrowFunctionExpression',
                        message: 'Arrow functions not supported in ES5 (iPad 2/iOS 9.3.5)',
                    },
                    {
                        selector: 'TemplateLiteral',
                        message: 'Template literals not supported in ES5 (iPad 2/iOS 9.3.5)',
                    },
                    {
                        selector: 'VariableDeclaration[kind="let"]',
                        message: 'let not supported in ES5 (iPad 2/iOS 9.3.5) - use var',
                    },
                    {
                        selector: 'VariableDeclaration[kind="const"]',
                        message: 'const not supported in ES5 (iPad 2/iOS 9.3.5) - use var',
                    },
                ],
            },
        },
        // Modern code - ES6+ allowed
        {
            files: [
                'app/static/js/main.js',
                'app/static/js/admin.js',
                'app/static/js/sw.js',
            ],
            parserOptions: {
                ecmaVersion: 2020,
            },
            env: {
                browser: true,
                es6: true,
            },
        },
    ],
    settings: {
        // For eslint-plugin-compat browser compatibility checking
        browserslist: [
            'iOS >= 9.3',
            'last 2 versions',
            '> 1%',
            'not dead',
        ],
        // Override for legacy files
        polyfills: ['Promise', 'fetch'],
    },
};
