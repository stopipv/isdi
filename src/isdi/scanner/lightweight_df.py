"""
Lightweight pandas alternative using pure Python.
Provides a minimal DataFrame-like interface without numpy/pandas overhead.
"""

import csv
from typing import List, Dict, Any, Optional, Union, Callable
from collections import defaultdict


class LightDataFrame:
    """
    A lightweight DataFrame alternative using pure Python dicts and lists.
    Supports common operations like read_csv, filter, merge, groupby, etc.
    """
    
    def __init__(self, data: Union[List[Dict], Dict] = None):
        """
        Initialize DataFrame from list of dicts or dict.
        
        Args:
            data: List of dicts (one per row) or single dict
        """
        if data is None:
            self.data = []
        elif isinstance(data, dict):
            # If it's a dict, treat as single row
            self.data = [data]
        elif isinstance(data, list):
            self.data = data
        else:
            self.data = list(data)
    
    @staticmethod
    def read_csv(file_path: str, encoding: str = 'utf-8', 
                 index_col: Optional[str] = None,
                 on_bad_lines: str = 'warn') -> 'LightDataFrame':
        """Read CSV file and return DataFrame."""
        data = []
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row is not None:
                        data.append(row)
        except FileNotFoundError:
            raise FileNotFoundError(f"Cannot find file: {file_path}")
        
        df = LightDataFrame(data)
        if index_col:
            df = df.set_index(index_col)
        return df
    
    @staticmethod
    def from_dict(data: Dict[str, List], orient: str = 'dict') -> 'LightDataFrame':
        """Create DataFrame from dict of lists (column-based) or list of dicts (records)."""
        if orient == 'dict' or orient == 'list':
            # data = {'col1': [1, 2, 3], 'col2': [4, 5, 6]}
            if not data:
                return LightDataFrame([])
            keys = list(data.keys())
            values = list(data.values())
            length = len(values[0]) if values else 0
            records = [{keys[i]: values[i][j] for i in range(len(keys))} 
                      for j in range(length)]
            return LightDataFrame(records)
        elif orient == 'records':
            # data = [{'col1': 1, 'col2': 4}, ...]
            return LightDataFrame(data)
        else:
            raise ValueError(f"Unsupported orient: {orient}")
    
    def fillna(self, value: Union[Any, Dict]) -> 'LightDataFrame':
        """Fill null values."""
        new_data = []
        for row in self.data:
            new_row = dict(row)
            if isinstance(value, dict):
                for k, v in value.items():
                    if new_row.get(k) in (None, '', 'nan'):
                        new_row[k] = v
            else:
                for k in new_row:
                    if new_row[k] in (None, '', 'nan'):
                        new_row[k] = value
            new_data.append(new_row)
        return LightDataFrame(new_data)
    
    def replace(self, old: Any, new: Any) -> 'LightDataFrame':
        """Replace values in all columns."""
        new_data = []
        for row in self.data:
            new_row = {k: (new if v == old else v) for k, v in row.items()}
            new_data.append(new_row)
        return LightDataFrame(new_data)
    
    def filter(self, func: Callable[[Dict], bool]) -> 'LightDataFrame':
        """Filter rows using a function."""
        return LightDataFrame([row for row in self.data if func(row)])
    
    def isin(self, column: str, values: set) -> 'LightDataFrame':
        """Filter rows where column value is in values set."""
        return self.filter(lambda row: row.get(column) in values)
    
    def query(self, condition: str) -> 'LightDataFrame':
        """Simple query support (limited)."""
        # Example: "flag.isin({'a', 'b'})" -> filter by flag
        # For now, just return self - full query syntax would be complex
        return self
    
    def set_index(self, column: str) -> 'IndexedDataFrame':
        """Set a column as index and return IndexedDataFrame."""
        index_dict = {}
        for row in self.data:
            if column in row:
                index_dict[row[column]] = row
        return IndexedDataFrame(self.data, index_col=column, index_dict=index_dict)
    
    def merge(self, other: 'LightDataFrame', on: str = None, 
              how: str = 'inner', left_on: str = None, 
              right_on: str = None) -> 'LightDataFrame':
        """Merge with another DataFrame."""
        if left_on is None:
            left_on = on
        if right_on is None:
            right_on = on
        
        # Build index for other DataFrame
        other_index = {}
        for row in other.data:
            key = row.get(right_on)
            if key:
                other_index[key] = row
        
        result = []
        
        if how == 'left':
            for row in self.data:
                key = row.get(left_on)
                if key in other_index:
                    # Merge the rows
                    merged = dict(row)
                    merged.update(other_index[key])
                    result.append(merged)
                else:
                    result.append(row)
        elif how == 'inner':
            for row in self.data:
                key = row.get(left_on)
                if key in other_index:
                    merged = dict(row)
                    merged.update(other_index[key])
                    result.append(merged)
        elif how == 'outer':
            # Left rows
            seen_keys = set()
            for row in self.data:
                key = row.get(left_on)
                seen_keys.add(key)
                if key in other_index:
                    merged = dict(row)
                    merged.update(other_index[key])
                    result.append(merged)
                else:
                    result.append(row)
            # Right-only rows
            for key, row in other_index.items():
                if key not in seen_keys:
                    result.append(row)
        
        return LightDataFrame(result)
    
    def groupby(self, column: str) -> 'GroupBy':
        """Group by a column."""
        groups = defaultdict(list)
        for row in self.data:
            key = row.get(column)
            groups[key].append(row)
        return GroupBy(groups, column)
    
    def sort_values(self, by: Union[str, List[str]], 
                   ascending: Union[bool, List[bool]] = True,
                   na_position: str = 'last') -> 'LightDataFrame':
        """Sort by column(s)."""
        if isinstance(by, str):
            by = [by]
        if isinstance(ascending, bool):
            ascending = [ascending] * len(by)
        
        def sort_key(row):
            keys = []
            for col, asc in zip(by, ascending):
                val = row.get(col)
                # Handle None/NaN
                if val is None or val == '' or val == 'nan':
                    if na_position == 'last':
                        val = (1, None)  # Sort to end
                    else:
                        val = (0, None)  # Sort to beginning
                else:
                    val = (0, val)
                
                if not asc:
                    # For descending, negate numeric values or reverse strings
                    if isinstance(val[1], (int, float)):
                        val = (val[0], -val[1])
                    else:
                        # Can't negate strings easily, just note the reversal
                        val = (val[0], val[1])
                keys.append(val)
            return keys
        
        sorted_data = sorted(self.data, key=sort_key)
        
        # Handle descending for strings and mixed
        if not all(ascending):
            # Re-sort with reverse for final columns
            for col, asc in reversed(list(zip(by, ascending))):
                sorted_data = sorted(sorted_data, 
                                   key=lambda row: self._sort_val(row.get(col)),
                                   reverse=not asc)
        
        return LightDataFrame(sorted_data)
    
    @staticmethod
    def _sort_val(val):
        """Convert value to sortable form."""
        if val is None or val == '' or val == 'nan':
            return (1, '')  # Sort nulls to end
        try:
            return (0, float(val))  # Try numeric
        except (ValueError, TypeError):
            return (0, str(val))  # Fall back to string
    
    def reset_index(self, drop: bool = False) -> 'LightDataFrame':
        """Reset index (no-op for LightDataFrame)."""
        return LightDataFrame(self.data)
    
    def select(self, columns: List[str]) -> 'LightDataFrame':
        """Select specific columns."""
        result = []
        for row in self.data:
            new_row = {col: row.get(col) for col in columns if col in row}
            result.append(new_row)
        return LightDataFrame(result)
    
    def with_columns(self, mappings: Dict[str, Callable]) -> 'LightDataFrame':
        """Add/update columns with mapped values."""
        new_data = []
        for row in self.data:
            new_row = dict(row)
            for col, func in mappings.items():
                new_row[col] = func(row)
            new_data.append(new_row)
        return LightDataFrame(new_data)
    
    def to_dict(self, orient: str = 'records') -> Union[List[Dict], Dict]:
        """Convert to dict."""
        if orient == 'records' or orient == 'list':
            return self.data
        elif orient == 'index':
            # Assumes first column can be used as index
            if not self.data:
                return {}
            index_col = list(self.data[0].keys())[0]
            return {row[index_col]: row for row in self.data if index_col in row}
        elif orient == 'dict':
            # Column-based dict
            if not self.data:
                return {}
            cols = set()
            for row in self.data:
                cols.update(row.keys())
            result = {col: [] for col in cols}
            for row in self.data:
                for col in cols:
                    result[col].append(row.get(col))
            return result
        else:
            raise ValueError(f"Unsupported orient: {orient}")
    
    def to_csv(self, file_path: str, index: bool = True) -> None:
        """Write to CSV file."""
        if not self.data:
            with open(file_path, 'w', newline='') as f:
                f.write('')
            return
        
        keys = list(self.data[0].keys())
        with open(file_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            for row in self.data:
                writer.writerow({k: row.get(k, '') for k in keys})
    
    def to_sql(self, table_name: str, connection, if_exists: str = 'replace') -> None:
        """Write to SQL database (requires sqlite3 cursor)."""
        import sqlite3
        
        if not self.data:
            return
        
        cursor = connection.cursor()
        keys = list(self.data[0].keys())
        
        if if_exists == 'replace':
            cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
        
        # Create table
        placeholders = ', '.join([f"{k} TEXT" for k in keys])
        cursor.execute(f"CREATE TABLE IF NOT EXISTS {table_name} ({placeholders})")
        
        # Insert data
        for row in self.data:
            values = [row.get(k, '') for k in keys]
            placeholders = ', '.join(['?' for _ in keys])
            cursor.execute(f"INSERT INTO {table_name} VALUES ({placeholders})", values)
        
        connection.commit()
    
    def __len__(self) -> int:
        return len(self.data)
    
    def __repr__(self) -> str:
        return f"LightDataFrame({len(self)} rows × {len(set().union(*[row.keys() for row in self.data]))} cols)"
    
    def __iter__(self):
        return iter(self.data)
    
    def head(self, n: int = 5) -> 'LightDataFrame':
        """Return first n rows."""
        return LightDataFrame(self.data[:n])
    
    def tail(self, n: int = 5) -> 'LightDataFrame':
        """Return last n rows."""
        return LightDataFrame(self.data[-n:])


class IndexedDataFrame(LightDataFrame):
    """DataFrame with an index column."""
    
    def __init__(self, data: List[Dict], index_col: str, index_dict: Dict = None):
        super().__init__(data)
        self.index_col = index_col
        self.index_dict = index_dict or {row.get(index_col): row for row in data}
    
    def loc(self, key: Any) -> Union[Dict, List]:
        """Access rows by index."""
        if key in self.index_dict:
            return self.index_dict[key]
        return None


class GroupBy:
    """Grouped data structure."""
    
    def __init__(self, groups: Dict[str, List[Dict]], column: str):
        self.groups = groups
        self.column = column
    
    def agg(self, agg_dict: Dict[str, Callable]) -> LightDataFrame:
        """Aggregate groups."""
        result = []
        for key, rows in self.groups.items():
            agg_row = {self.column: key}
            for col, func in agg_dict.items():
                if col == self.column:
                    continue
                values = [row.get(col) for row in rows]
                if func == 'sum':
                    agg_row[col] = sum(v for v in values if v)
                elif func == 'mean':
                    nums = [float(v) for v in values if v]
                    agg_row[col] = sum(nums) / len(nums) if nums else 0
                elif func == 'count':
                    agg_row[col] = len(values)
                elif func == 'list':
                    agg_row[col] = values
                elif callable(func):
                    agg_row[col] = func(values)
                else:
                    agg_row[col] = func
            result.append(agg_row)
        return LightDataFrame(result)
    
    def apply(self, func: Callable) -> List:
        """Apply function to each group."""
        return [func(rows) for rows in self.groups.values()]
