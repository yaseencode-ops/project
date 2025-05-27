from transformers import RobertaTokenizer, RobertaForSequenceClassification
import torch
import logging
import ast
import re
import importlib
import os
import sys
import tokenize
from io import StringIO

class CodeReviewModel:
    def __init__(self):
        self.model = None
        self.tokenizer = None
        try:
            print("Loading model and tokenizer...")
            self.tokenizer = RobertaTokenizer.from_pretrained('microsoft/codebert-base')
            self.model = RobertaForSequenceClassification.from_pretrained('microsoft/codebert-base', num_labels=2)
            print("Model loaded successfully")
        except Exception as e:
            print(f"Error loading model: {str(e)}")
            raise RuntimeError(f"Failed to initialize model: {str(e)}")
    
    def get_line_number(self, code, error_node):
        """Get line number for an AST node"""
        return getattr(error_node, 'lineno', 0)
    
    def check_syntax(self, code_snippet):
        """Check if the code has valid Python syntax"""
        try:
            ast.parse(code_snippet)
            return True, None
        except SyntaxError as e:
            return False, f"Syntax Error on line {e.lineno}: {str(e)}"
        except Exception as e:
            return False, f"Parse Error: {str(e)}"
    
    def check_imports(self, code_snippet):
        """Check for import errors"""
        issues = []
        try:
            tree = ast.parse(code_snippet)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for name in node.names:
                        try:
                            importlib.import_module(name.name)
                        except ImportError:
                            issues.append({
                                'severity': 'error',
                                'message': f"Line {node.lineno}: ModuleNotFoundError: No module named '{name.name}'",
                                'line': node.lineno,
                                'confidence': 1.0
                            })
                elif isinstance(node, ast.ImportFrom):
                    try:
                        importlib.import_module(node.module)
                    except ImportError:
                        issues.append({
                            'severity': 'error',
                            'message': f"Line {node.lineno}: ModuleNotFoundError: No module named '{node.module}'",
                            'line': node.lineno,
                            'confidence': 1.0
                        })
        except:
            pass
        return issues

    def check_file_operations(self, code_snippet):
        """Check for file operation issues"""
        issues = []
        try:
            tree = ast.parse(code_snippet)
            for node in ast.walk(tree):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == 'open':
                    if len(node.args) > 0 and isinstance(node.args[0], ast.Str):
                        filepath = node.args[0].s
                        if not os.path.exists(filepath):
                            issues.append({
                                'severity': 'warning',
                                'message': f"Line {node.lineno}: FileNotFoundError: File '{filepath}' might not exist",
                                'line': node.lineno,
                                'confidence': 0.8
                            })
        except:
            pass
        return issues

    def check_common_errors(self, code_snippet):
        """Check for common programming errors"""
        issues = []
        try:
            tree = ast.parse(code_snippet)
            for node in ast.walk(tree):
                # Check for infinite loops
                if isinstance(node, ast.While):
                    if isinstance(node.test, ast.Constant) and node.test.value is True:
                        has_break = any(isinstance(n, ast.Break) for n in ast.walk(node))
                        if not has_break:
                            issues.append({
                                'severity': 'warning',
                                'message': f"Line {node.lineno}: Potential infinite loop detected (while True without break)",
                                'line': node.lineno,
                                'confidence': 0.9
                            })

                # Check for bare except clauses
                if isinstance(node, ast.ExceptHandler) and node.type is None:
                    issues.append({
                        'severity': 'medium',
                        'message': f"Line {node.lineno}: Bare except clause detected - consider catching specific exceptions",
                        'line': node.lineno,
                        'confidence': 0.95
                    })

                # Check for global variables
                if isinstance(node, ast.Global):
                    issues.append({
                        'severity': 'medium',
                        'message': f"Line {node.lineno}: Use of global variables detected - consider alternative approaches",
                        'line': node.lineno,
                        'confidence': 0.9
                    })

        except:
            pass
        return issues
            
    def check_all_errors(self, code_snippet):
        """Check for all possible errors and code quality issues"""
        issues = []
        
        try:
            tree = ast.parse(code_snippet)
            
            # Check variable naming
            for node in ast.walk(tree):
                if isinstance(node, ast.Name):
                    # Check for single letter variables
                    if len(node.id) == 1 and node.id not in ['i', 'j', 'k', 'n', 'm']:
                        issues.append({
                            'severity': 'low',
                            'message': f"Line {node.lineno}: Single letter variable '{node.id}' detected - consider using more descriptive names",
                            'line': node.lineno,
                            'confidence': 0.8
                        })
                    
                    # Check for snake_case naming convention
                    if not node.id.islower() and '_' not in node.id:
                        issues.append({
                            'severity': 'low',
                            'message': f"Line {node.lineno}: Variable '{node.id}' should use snake_case naming convention",
                            'line': node.lineno,
                            'confidence': 0.9
                        })
                
                # Check function complexity
                elif isinstance(node, ast.FunctionDef):
                    # Count number of branches (if/for/while statements)
                    branches = len([n for n in ast.walk(node) if isinstance(n, (ast.If, ast.For, ast.While))])
                    if branches > 5:
                        issues.append({
                            'severity': 'medium',
                            'message': f"Line {node.lineno}: Function '{node.name}' has high cyclomatic complexity ({branches} branches)",
                            'line': node.lineno,
                            'confidence': 0.9
                        })
                    
                    # Check function length
                    if len(node.body) > 15:
                        issues.append({
                            'severity': 'medium',
                            'message': f"Line {node.lineno}: Function '{node.name}' is too long ({len(node.body)} lines)",
                            'line': node.lineno,
                            'confidence': 0.9
                        })
                    
                    # Check number of arguments
                    if len(node.args.args) > 5:
                        issues.append({
                            'severity': 'medium',
                            'message': f"Line {node.lineno}: Function '{node.name}' has too many parameters ({len(node.args.args)})",
                            'line': node.lineno,
                            'confidence': 0.9
                        })
                
                # Check for nested loops
                elif isinstance(node, (ast.For, ast.While)):
                    nested = any(isinstance(n, (ast.For, ast.While)) for n in ast.walk(node))
                    if nested:
                        issues.append({
                            'severity': 'medium',
                            'message': f"Line {node.lineno}: Nested loop detected - consider refactoring",
                            'line': node.lineno,
                            'confidence': 0.8
                        })
        except:
            pass
        
        return issues

    def get_suggestion(self, issue_type, message):
        """Get improvement suggestions based on the issue type and message"""
        suggestions = {
            'data': {
                'missing': 'Add data validation checks using assert or if statements',
                'null': 'Handle null values using fillna() or dropna()',
                'format': 'Use data preprocessing techniques like StandardScaler or MinMaxScaler',
                'input': 'Implement input validation using type hints or validation functions'
            },
            'model': {
                'initialization': 'Initialize model with proper architecture and parameters',
                'weights': 'Use proper weight initialization techniques like Xavier or He initialization',
                'bias': 'Consider adding bias terms to improve model flexibility',
                'prediction': 'Add prediction error handling and validation'
            },
            'algorithm': {
                'training': 'Implement early stopping and learning rate scheduling',
                'gradient': 'Use gradient clipping to prevent exploding gradients',
                'loss': 'Consider using a different loss function more suitable for your task',
                'optimization': 'Try different optimizers like Adam or RMSprop'
            },
            'hyperparameter': {
                'tuning': 'Use grid search or random search for hyperparameter optimization',
                'optimization': 'Implement cross-validation for better parameter selection',
                'learning_rate': 'Try learning rate scheduling or adaptive learning rates',
                'batch_size': 'Experiment with different batch sizes for better performance'
            },
            'evaluation': {
                'metrics': 'Add multiple evaluation metrics (accuracy, precision, recall, F1)',
                'validation': 'Implement k-fold cross-validation',
                'testing': 'Create separate test sets for final evaluation',
                'performance': 'Add performance monitoring and logging'
            },
            'deployment': {
                'production': 'Add model versioning and deployment pipeline',
                'service': 'Implement API endpoints with proper error handling',
                'monitoring': 'Add monitoring and logging for production environment',
                'scaling': 'Consider using model compression or quantization'
            },
            'syntax': {
                'naming': 'Follow PEP 8 naming conventions',
                'indent': 'Use 4 spaces for indentation',
                'import': 'Organize imports and remove unused ones',
                'structure': 'Break down complex functions into smaller ones'
            },
            'runtime': {
                'memory': 'Optimize memory usage with generators or batch processing',
                'performance': 'Use vectorized operations instead of loops where possible',
                'error': 'Add proper error handling with try-except blocks',
                'infinite': 'Add break conditions or maximum iteration limits'
            }
        }

        # Find matching suggestion category
        for category, patterns in suggestions.items():
            for key, suggestion in patterns.items():
                if key in message.lower():
                    return suggestion

        # Default suggestions based on severity
        return {
            'error': 'Review and fix the error following Python best practices',
            'high': 'Consider refactoring this section for better reliability',
            'medium': 'Improve code quality by following ML best practices',
            'low': 'Optional: Consider enhancing this part of the code',
        }.get(issue_type, 'Review and improve following ML best practices')

    def analyze_code(self, code_snippet):
        if self.model is None or self.tokenizer is None:
            return [{'severity': 'error', 
                    'message': 'Model not properly initialized',
                    'line': 0, 
                    'confidence': 1.0}]

        try:
            issues = []
            
            # Check for empty code
            if not code_snippet.strip():
                return [{'severity': 'high', 
                        'message': 'Empty code submitted',
                        'line': 0,
                        'confidence': 1.0}]
            
            # Check syntax first
            is_valid_syntax, syntax_error = self.check_syntax(code_snippet)
            if not is_valid_syntax:
                return [{'severity': 'error',
                        'message': syntax_error,
                        'line': int(re.search(r'line (\d+)', syntax_error or '0').group(1) or 0),
                        'confidence': 1.0}]

            # Run all checks
            issues.extend(self.check_imports(code_snippet))
            issues.extend(self.check_file_operations(code_snippet))
            issues.extend(self.check_common_errors(code_snippet))
            issues.extend(self.check_all_errors(code_snippet))

            # Process the code line by line
            lines = code_snippet.split('\n')
            for i, line in enumerate(lines, 1):
                # Check line length
                if len(line) > 79:
                    issues.append({
                        'severity': 'low',
                        'message': f'Line {i} is too long ({len(line)} characters)',
                        'line': i,
                        'confidence': 0.9
                    })
                
                # Check indentation
                if line.startswith(' ') and not line.startswith('    '):
                    issues.append({
                        'severity': 'medium',
                        'message': f'Line {i} has incorrect indentation - use 4 spaces',
                        'line': i,
                        'confidence': 0.9
                    })
                
                # Check for commented-out code
                if line.strip().startswith('#') and any(keyword in line for keyword in ['def ', 'class ', 'if ', 'for ', 'while ']):
                    issues.append({
                        'severity': 'low',
                        'message': f'Line {i} appears to contain commented-out code',
                        'line': i,
                        'confidence': 0.7
                    })

            # Model-based analysis
            inputs = self.tokenizer(code_snippet, return_tensors="pt", truncation=True, max_length=512)
            outputs = self.model(**inputs)
            predictions = torch.nn.functional.softmax(outputs.logits, dim=-1)
            confidence = float(predictions[0][1])
            
            if confidence > 0.5:
                issues.append({
                    'severity': 'high',
                    'message': 'Potential code quality issues detected',
                    'line': 0,
                    'confidence': confidence
                })

            # Add suggestions to each issue
            for issue in issues:
                issue['suggestion'] = self.get_suggestion(issue['severity'], issue['message'])

            # Sort issues by line number and severity
            issues.sort(key=lambda x: (x['line'], {'error': 0, 'high': 1, 'medium': 2, 'low': 3}.get(x['severity'], 4)))
            
            print(f"Analysis complete. Found {len(issues)} issues")
            return issues if issues else [{'severity': 'success', 
                                         'message': 'No significant issues found',
                                         'line': 0,
                                         'suggestion': 'Code looks good! Consider adding more tests and documentation.',
                                         'confidence': 1.0}]
            
        except Exception as e:
            error_msg = f"Error during analysis: {str(e)}"
            print(error_msg)
            return [{'severity': 'error', 
                    'message': error_msg,
                    'line': 0,
                    'suggestion': 'Fix the syntax error and try again',
                    'confidence': 1.0}] 