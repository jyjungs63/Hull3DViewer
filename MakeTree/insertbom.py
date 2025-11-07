import pandas as pd
import mysql.connector
from mysql.connector import errorcode
import os
import glob
from datetime import datetime

# 데이터베이스 설정
DB_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'root',
    'password': 'manager',
    'database': 'hull3d',
    'charset': 'utf8mb4',
    'shipno_default': '1000'
}

# 대상 디렉토리
TARGET_DIRECTORY = r"D:\hull3dviewer\MakeTree\ASSYPARTLIST\\"

# INSERT/UPDATE 쿼리 (shipno, name 복합키 기준)
INSERT_QUERY = """
INSERT INTO material_list 
(shipno, name, type, description, quantity, manufac_qual, pos_no, weight, cog_x, cog_y, cog_z, comment) 
VALUES (
    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
)
ON DUPLICATE KEY UPDATE
    type=VALUES(type),
    description=VALUES(description),
    quantity=VALUES(quantity),
    manufac_qual=VALUES(manufac_qual),
    pos_no=VALUES(pos_no),
    weight=VALUES(weight),
    cog_x=VALUES(cog_x),
    cog_y=VALUES(cog_y),
    cog_z=VALUES(cog_z),
    comment=VALUES(comment);
"""

# 엑셀 컬럼 매핑 (여러 가능한 이름 패턴)
EXCEL_COLUMN_PATTERNS = {
    'NAME': ['NAME', 'PART_NAME', 'PARTNAME', '품명', '부품명'],
    'TYPE': ['TYPE', 'PART_TYPE', 'PARTTYPE', '타입', '형식'],
    'DESCRIPTION': ['DESCRIPTION', 'DESC', 'SPEC', '설명', '사양'],
    'QUANTITY': ['QUANTITY', 'QTY', 'Q\'TY', '수량'],
    'MANUFAC_QUAL': ['MANUFAC_QUAL', 'MANUFAC QUAL', 'MFG_QUAL', 'QUALITY', '품질'],
    'POS_NO': ['POS_NO', 'POS NO', 'POSITION', 'POS', '위치'],
    'WEIGHT': ['WEIGHT', 'WT', 'MASS', '중량'],
    'COG_X': ['COG_X', 'COG X', 'COGX', 'CG_X', 'X'],
    'COG_Y': ['COG_Y', 'COG Y', 'COGY', 'CG_Y', 'Y'],
    'COG_Z': ['COG_Z', 'COG Z', 'COGZ', 'CG_Z', 'Z'],
    'COMMENT': ['COMMENT', 'COMMENTS', 'NOTE', 'NOTES', 'REMARK', '비고', '주석']
}

# 기본 컬럼 순서
EXCEL_COLUMNS = list(EXCEL_COLUMN_PATTERNS.keys())


def log_message(message, level="INFO"):
    """로그 메시지 출력"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    symbols = {
        "INFO": "ℹ️",
        "SUCCESS": "✅",
        "WARNING": "⚠️",
        "ERROR": "❌",
        "START": "✨"
    }
    symbol = symbols.get(level, "•")
    print(f"[{timestamp}] {symbol} {message}")


def get_excel_files(directory):
    """디렉토리에서 Excel 파일 목록 가져오기"""
    if not os.path.exists(directory):
        log_message(f"디렉토리가 존재하지 않습니다: {directory}", "ERROR")
        return []
    
    patterns = [
        os.path.join(directory, '*.xlsx'),
        os.path.join(directory, '*.xls')
    ]
    
    files = []
    for pattern in patterns:
        files.extend(glob.glob(pattern))
    
    # 임시파일(~$) 및 숨김파일 필터링
    files = [f for f in files if not os.path.basename(f).startswith('~$') 
             and not os.path.basename(f).startswith('.')]
    
    return sorted(files)


def guess_engine_by_extension(path):
    """파일 확장자에 따라 적절한 pandas 엔진 추천"""
    ext = os.path.splitext(path)[1].lower()
    if ext == '.xlsx':
        return 'openpyxl'
    elif ext == '.xls':
        return 'xlrd'
    return None


def safe_parse_float(value):
    """안전하게 float로 변환"""
    if value is None or pd.isna(value):
        return None
    
    # 이미 숫자 타입인 경우
    if isinstance(value, (int, float)):
        return float(value)
    
    # 문자열 처리
    s = str(value).strip()
    if s == '' or s.lower() in ['nan', 'none', 'null']:
        return None
    
    # 쉼표, 공백 제거
    s = s.replace(',', '').replace('\u00A0', '').replace(' ', '')
    
    # 괄호로 감싼 음수 처리 (예: (123.45) -> -123.45)
    if s.startswith('(') and s.endswith(')'):
        s = '-' + s[1:-1]
    
    try:
        return float(s)
    except (ValueError, TypeError):
        log_message(f"숫자 변환 실패: '{value}'", "WARNING")
        return None


def safe_parse_int(value):
    """안전하게 int로 변환"""
    if value is None or pd.isna(value):
        return None
    
    if isinstance(value, int):
        return value
    
    if isinstance(value, float):
        return int(value)
    
    s = str(value).strip().replace(',', '').replace(' ', '')
    if s == '' or s.lower() in ['nan', 'none', 'null']:
        return None
    
    try:
        return int(float(s))
    except (ValueError, TypeError):
        log_message(f"정수 변환 실패: '{value}'", "WARNING")
        return None


def normalize_columns(columns):
    """컬럼명 정규화 (공백 정리, 대문자 변환)"""
    normalized_map = {}
    for col in columns:
        if isinstance(col, str):
            # 여러 공백을 하나로, 앞뒤 공백 제거, 대문자 변환
            normalized = ' '.join(col.strip().split()).upper()
            normalized_map[normalized] = col
        else:
            # 숫자 등 비문자열 컬럼명
            normalized = str(col).upper()
            normalized_map[normalized] = col
    
    return normalized_map


def read_excel_file(file_path):
    """Excel 파일 읽기 (여러 엔진 시도)"""
    log_message(f"파일 읽기 시도: {os.path.basename(file_path)}", "START")
    
    # 시도할 엔진 목록
    engines_to_try = []
    
    # 확장자 기반 추천 엔진
    recommended_engine = guess_engine_by_extension(file_path)
    if recommended_engine:
        engines_to_try.append(recommended_engine)
    
    # Fallback 엔진들
    engines_to_try.extend(['openpyxl', 'xlrd', None])
    
    last_error = None
    
    for engine in engines_to_try:
        try:
            if engine is None:
                df = pd.read_excel(file_path)
                log_message(f"읽기 성공 (pandas 자동 선택)", "SUCCESS")
            else:
                df = pd.read_excel(file_path, engine=engine)
                log_message(f"읽기 성공 (engine={engine})", "SUCCESS")
            
            return df
            
        except Exception as e:
            last_error = e
            log_message(f"engine={engine} 실패: {str(e)[:100]}", "WARNING")
    
    log_message(f"모든 엔진 시도 실패: {last_error}", "ERROR")
    return None


def validate_columns(df, required_patterns):
    """필수 컬럼 존재 여부 확인 (유연한 매칭)"""
    # 실제 컬럼 정규화
    normalized_actual = normalize_columns(df.columns)
    
    log_message(f"Excel 파일의 실제 컬럼명: {list(df.columns)}", "INFO")
    log_message(f"정규화된 컬럼명: {list(normalized_actual.keys())}", "INFO")
    
    # 컬럼 매핑 결과 저장
    column_mapping = {}
    missing_columns = []
    
    # 각 필수 컬럼에 대해 매칭 시도
    for required_col in EXCEL_COLUMNS:
        patterns = EXCEL_COLUMN_PATTERNS.get(required_col, [required_col])
        normalized_patterns = [' '.join(p.strip().split()).upper() for p in patterns]
        
        matched = False
        for pattern in normalized_patterns:
            if pattern in normalized_actual:
                column_mapping[required_col] = normalized_actual[pattern]
                matched = True
                log_message(f"✓ {required_col} → '{normalized_actual[pattern]}'", "SUCCESS")
                break
        
        if not matched:
            missing_columns.append(required_col)
            log_message(f"✗ {required_col} - 매칭 실패 (시도: {patterns})", "WARNING")
    
    if missing_columns:
        log_message(f"매칭되지 않은 필수 컬럼: {missing_columns}", "ERROR")
        log_message("해결 방법:", "INFO")
        log_message("1. Excel 파일의 컬럼명을 위의 '실제 컬럼명'과 비교하세요", "INFO")
        log_message("2. 필요시 EXCEL_COLUMN_PATTERNS에 새로운 패턴을 추가하세요", "INFO")
        return None
    
    # 원본 컬럼명 순서대로 반환
    selected_columns = [column_mapping[col] for col in EXCEL_COLUMNS]
    
    return selected_columns


def prepare_row_data(row, selected_columns, shipno):
    """행 데이터를 DB 삽입 형식으로 준비"""
    values = [row[col] for col in selected_columns]
    insert_data = [shipno] + values
    
    # NaN을 None으로 변환
    insert_data = [None if pd.isna(x) else x for x in insert_data]
    
    # 데이터 타입 변환
    # insert_data 인덱스: 0=shipno, 1=name, 2=type, 3=description, 4=quantity,
    #                     5=manufac_qual, 6=pos_no, 7=weight, 8=cog_x, 9=cog_y, 10=cog_z, 11=comment
    
    # pos_no (인덱스 6): 정수 변환
    insert_data[6] = safe_parse_int(insert_data[6])
    
    # weight, cog_x, cog_y, cog_z (인덱스 7-10): 실수 변환
    for i in range(7, 11):
        insert_data[i] = safe_parse_float(insert_data[i])
    
    return tuple(insert_data)


def load_excel_to_db(file_path, db_config):
    """Excel 파일을 DB에 로드"""
    log_message(f"\n{'='*80}\n파일 처리 시작: {os.path.basename(file_path)}\n{'='*80}", "START")
    
    # Excel 파일 읽기
    df = read_excel_file(file_path)
    if df is None:
        return False
    
    log_message(f"총 {len(df)}개 행 읽음", "INFO")
    
    # 컬럼 검증
    selected_columns = validate_columns(df, EXCEL_COLUMN_PATTERNS)
    if selected_columns is None:
        return False
    
    # 선택된 컬럼만 사용
    df = df[selected_columns]
    
    # 데이터베이스 연결 및 삽입
    conn = None
    cursor = None
    success = False
    
    try:
        # DB 연결
        log_message("데이터베이스 연결 중...", "INFO")
        conn = mysql.connector.connect(
            host=db_config['host'],
            port=db_config['port'],
            user=db_config['user'],
            password=db_config['password'],
            database=db_config['database'],
            charset=db_config['charset']
        )
        cursor = conn.cursor()
        log_message("데이터베이스 연결 성공", "SUCCESS")
        
        # 데이터 준비
        shipno = db_config.get('shipno_default', '1000')
        data_to_insert = []
        
        for idx, row in df.iterrows():
            try:
                prepared_data = prepare_row_data(row, selected_columns, shipno)
                data_to_insert.append(prepared_data)
            except Exception as e:
                log_message(f"행 {idx+2} 처리 중 오류: {e}", "WARNING")
        
        # DB에 삽입
        if data_to_insert:
            log_message(f"{len(data_to_insert)}개 레코드 삽입/업데이트 중...", "INFO")
            cursor.executemany(INSERT_QUERY, data_to_insert)
            conn.commit()
            log_message(f"{cursor.rowcount}개 레코드 처리 완료", "SUCCESS")
            success = True
        else:
            log_message("삽입할 데이터가 없습니다", "WARNING")
    
    except mysql.connector.Error as err:
        if conn and conn.is_connected():
            try:
                conn.rollback()
                log_message("트랜잭션 롤백됨", "WARNING")
            except:
                pass
        
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            log_message("사용자 이름 또는 비밀번호가 잘못되었습니다", "ERROR")
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            log_message("데이터베이스가 존재하지 않습니다", "ERROR")
        else:
            log_message(f"데이터베이스 오류: {err}", "ERROR")
    
    except Exception as e:
        log_message(f"일반 오류: {e}", "ERROR")
        import traceback
        traceback.print_exc()
    
    finally:
        # 리소스 정리
        if cursor:
            try:
                cursor.close()
            except:
                pass
        
        if conn and conn.is_connected():
            try:
                conn.close()
                log_message("데이터베이스 연결 종료", "INFO")
            except:
                pass
    
    return success


def main():
    """메인 실행 함수"""
    log_message("\n" + "="*80, "START")
    log_message("Excel to MySQL 업로드 프로그램 시작", "START")
    log_message("="*80 + "\n", "START")
    
    # Excel 파일 목록 가져오기
    excel_files = get_excel_files(TARGET_DIRECTORY)
    
    if not excel_files:
        log_message(f"디렉토리에서 Excel 파일을 찾을 수 없습니다: {TARGET_DIRECTORY}", "WARNING")
        return
    
    log_message(f"총 {len(excel_files)}개 파일 발견", "INFO")
    
    # 각 파일 처리
    success_count = 0
    fail_count = 0
    
    for excel_file in excel_files:
        if load_excel_to_db(excel_file, DB_CONFIG):
            success_count += 1
        else:
            fail_count += 1
    
    # 최종 결과
    log_message("\n" + "="*80, "SUCCESS")
    log_message(f"처리 완료 - 성공: {success_count}, 실패: {fail_count}", "SUCCESS")
    log_message("="*80 + "\n", "SUCCESS")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log_message("\n사용자에 의해 중단되었습니다", "WARNING")
    except Exception as e:
        log_message(f"예상치 못한 오류: {e}", "ERROR")
        import traceback
        traceback.print_exc()