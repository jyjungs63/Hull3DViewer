import pandas as pd
import os
import glob

# 대상 디렉토리
TARGET_DIRECTORY = r"D:\hull3dviewer\MakeTree\ASSYPARTLIST\\"

def get_excel_files(directory):
    """디렉토리에서 Excel 파일 목록 가져오기"""
    if not os.path.exists(directory):
        print(f"❌ 디렉토리가 존재하지 않습니다: {directory}")
        return []
    
    patterns = [
        os.path.join(directory, '*.xlsx'),
        os.path.join(directory, '*.xls')
    ]
    
    files = []
    for pattern in patterns:
        files.extend(glob.glob(pattern))
    
    # 임시파일(~$) 필터링
    files = [f for f in files if not os.path.basename(f).startswith('~$')]
    
    return sorted(files)


def check_excel_columns(file_path):
    """Excel 파일의 컬럼명 확인"""
    print(f"\n{'='*80}")
    print(f"파일: {os.path.basename(file_path)}")
    print(f"{'='*80}")
    
    engines = ['openpyxl', 'xlrd', None]
    
    for engine in engines:
        try:
            if engine is None:
                df = pd.read_excel(file_path)
                print(f"✅ 읽기 성공 (pandas 자동)")
            else:
                df = pd.read_excel(file_path, engine=engine)
                print(f"✅ 읽기 성공 (engine={engine})")
            
            print(f"\n📋 총 {len(df.columns)}개의 컬럼 발견:")
            print("-" * 80)
            
            for idx, col in enumerate(df.columns, 1):
                col_type = type(col).__name__
                print(f"  {idx:2d}. [{col_type:10s}] '{col}'")
            
            print("\n📊 각 컬럼의 샘플 데이터 (첫 3행):")
            print("-" * 80)
            print(df.head(3).to_string())
            
            return True
            
        except Exception as e:
            print(f"⚠️  engine={engine} 실패: {e}")
    
    print("❌ 모든 엔진 시도 실패")
    return False


if __name__ == "__main__":
    print("="*80)
    print("Excel 파일 컬럼명 확인 도구")
    print("="*80)
    
    excel_files = get_excel_files(TARGET_DIRECTORY)
    
    if not excel_files:
        print(f"\n⚠️  디렉토리에서 Excel 파일을 찾을 수 없습니다: {TARGET_DIRECTORY}")
    else:
        print(f"\n📁 총 {len(excel_files)}개 파일 발견\n")
        
        for excel_file in excel_files:
            check_excel_columns(excel_file)
            print("\n")
        
        print("="*80)
        print("✅ 모든 파일 확인 완료")
        print("="*80)