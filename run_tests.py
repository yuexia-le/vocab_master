# run_tests.py (支持 Allure 版)
import sys
import pytest
import argparse
import os
import shutil

def print_header(text):
    print("\n" + "=" * 60)
    print(f"📊 {text}")
    print("=" * 60 + "\n")

def main():
    parser = argparse.ArgumentParser(description='Word-Lingo 测试运行工具')
    parser.add_argument('--unit', action='store_true', help='运行单元测试')
    parser.add_argument('--integration', action='store_true', help='运行集成测试')
    parser.add_argument('--e2e', action='store_true', help='运行端到端流程测试')
    parser.add_argument('--all', action='store_true', help='运行所有测试')
    parser.add_argument('--allure', action='store_true', help='生成 Allure 可视化报告数据')

    args = parser.parse_args()
    
    # 基础参数
    pytest_args = ['-v', '--tb=short']
    
    # 定义 Allure 结果存放路径
    results_dir = "tests/report/allure_results"

    if args.allure:
        # 如果目录已存在则清空，保证数据最新
        if os.path.exists(results_dir):
            shutil.rmtree(results_dir)
        pytest_args.append(f'--alluredir={results_dir}')

    # 确定测试路径和标记
    if args.unit:
        print_header("运行单元测试")
        pytest_args.extend(['tests/unit/', '-m', 'unit'])
    elif args.integration:
        print_header("运行集成测试.")
        pytest_args.extend(['tests/integration/', '-m', 'integration'])
    elif args.e2e:
        print_header("运行端到端测试")
        pytest_args.extend(['tests/integration/', '-m', 'e2e'])
    elif args.all:
        print_header("运行所有测试")
        pytest_args.append('tests/')
    else:
        print_header("默认运行所有测试并生成 Allure 数据")
        pytest_args.extend(['tests/', f'--alluredir={results_dir}'])

    exit_code = pytest.main(pytest_args)

    # 如果开启了 allure 并且测试执行完毕，提示用户如何查看
    if args.allure:
        print("\n" + "-" * 60)
        print(f"✅ 测试结果数据已存入: {results_dir}")
        print("💡 请运行以下命令查看可视化报告:")
        print(f"   allure serve {results_dir}")
        print("-" * 60)

    return exit_code

if __name__ == '__main__':
    sys.exit(main())