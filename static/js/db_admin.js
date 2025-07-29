// 数据库管理页面JavaScript

let selectedRecords = [];

// 加载所有记录
function loadRecords() {
    fetch('/db_admin/records')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                displayRecords(data.records);
                document.getElementById('dataTableContainer').style.display = 'block';
            } else {
                alert('加载数据失败: ' + data.error);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('加载数据时发生错误');
        });
}

// 显示记录
function displayRecords(records) {
    const tbody = document.getElementById('dataTableBody');
    tbody.innerHTML = '';
    
    records.forEach(record => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td><input type="checkbox" class="record-checkbox" value="${record.id}"></td>
            <td>${record.id}</td>
            <td>${record.record_date}</td>
            <td>${record.channel}</td>
            <td>${record.fee_type}</td>
            <td>${record.room_nights || 0}</td>
            <td>¥${parseFloat(record.revenue || 0).toFixed(2)}</td>
            <td>${record.order_id || ''}</td>
            <td>${record.guest_name || ''}</td>
            <td>
                <button class="btn btn-sm btn-primary" onclick="editRecord(${record.id})">
                    <i class="fas fa-edit"></i>
                </button>
                <button class="btn btn-sm btn-danger" onclick="deleteRecord(${record.id})">
                    <i class="fas fa-trash"></i>
                </button>
            </td>
        `;
        tbody.appendChild(row);
    });
    
    // 添加复选框事件监听
    document.querySelectorAll('.record-checkbox').forEach(checkbox => {
        checkbox.addEventListener('change', updateSelectedRecords);
    });
}

// 更新选中的记录
function updateSelectedRecords() {
    selectedRecords = Array.from(document.querySelectorAll('.record-checkbox:checked'))
        .map(checkbox => parseInt(checkbox.value));
}

// 全选
function selectAll() {
    document.querySelectorAll('.record-checkbox').forEach(checkbox => {
        checkbox.checked = true;
    });
    document.getElementById('selectAllCheckbox').checked = true;
    updateSelectedRecords();
}

// 取消全选
function selectNone() {
    document.querySelectorAll('.record-checkbox').forEach(checkbox => {
        checkbox.checked = false;
    });
    document.getElementById('selectAllCheckbox').checked = false;
    updateSelectedRecords();
}

// 编辑记录
function editRecord(id) {
    fetch(`/db_admin/record/${id}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                const record = data.record;
                document.getElementById('editId').value = record.id;
                document.getElementById('editDate').value = record.record_date;
                document.getElementById('editChannel').value = record.channel;
                document.getElementById('editFeeType').value = record.fee_type;
                document.getElementById('editRoomNights').value = record.room_nights || 0;
                document.getElementById('editRevenue').value = record.revenue || 0;
                document.getElementById('editGuestName').value = record.guest_name || '';
                
                $('#editModal').modal('show');
            } else {
                alert('获取记录失败: ' + data.error);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('获取记录时发生错误');
        });
}

// 保存编辑
function saveEdit() {
    const formData = {
        id: document.getElementById('editId').value,
        record_date: document.getElementById('editDate').value,
        channel: document.getElementById('editChannel').value,
        fee_type: document.getElementById('editFeeType').value,
        room_nights: parseFloat(document.getElementById('editRoomNights').value) || 0,
        revenue: parseFloat(document.getElementById('editRevenue').value) || 0,
        guest_name: document.getElementById('editGuestName').value
    };
    
    fetch('/db_admin/update', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(formData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            $('#editModal').modal('hide');
            loadRecords(); // 重新加载数据
            alert('记录更新成功');
        } else {
            alert('更新失败: ' + data.error);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('更新时发生错误');
    });
}

// 删除单个记录
function deleteRecord(id) {
    if (confirm('确定要删除这条记录吗？此操作不可恢复！')) {
        fetch(`/db_admin/delete/${id}`, {
            method: 'DELETE'
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                loadRecords(); // 重新加载数据
                alert('记录删除成功');
            } else {
                alert('删除失败: ' + data.error);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('删除时发生错误');
        });
    }
}

// 确认删除选中记录
function confirmDeleteSelected() {
    if (selectedRecords.length === 0) {
        alert('请先选择要删除的记录');
        return;
    }
    
    if (confirm(`确定要删除选中的 ${selectedRecords.length} 条记录吗？此操作不可恢复！`)) {
        fetch('/db_admin/delete_batch', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ids: selectedRecords})
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                loadRecords(); // 重新加载数据
                alert(`成功删除 ${data.deleted_count} 条记录`);
            } else {
                alert('批量删除失败: ' + data.error);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('批量删除时发生错误');
        });
    }
}

// 确认清空所有数据
function confirmClearAll() {
    const confirmation = prompt('此操作将删除所有数据！请输入 "DELETE ALL" 确认：');
    if (confirmation === 'DELETE ALL') {
        fetch('/db_admin/clear_all', {
            method: 'POST'
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                loadRecords(); // 重新加载数据
                alert('所有数据已清空');
            } else {
                alert('清空失败: ' + data.error);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('清空时发生错误');
        });
    } else if (confirmation !== null) {
        alert('确认文本不正确，操作已取消');
    }
}

// 备份数据库
function confirmBackup() {
    if (confirm('确定要备份数据库吗？')) {
        fetch('/db_admin/backup', {
            method: 'POST'
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert('数据库备份成功: ' + data.backup_file);
            } else {
                alert('备份失败: ' + data.error);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('备份时发生错误');
        });
    }
}

// 导出数据
function exportData() {
    window.open('/db_admin/export', '_blank');
}

// 显示批量编辑
function showBulkEdit() {
    alert('批量编辑功能开发中...');
}

// 按日期范围删除数据
function confirmDeleteByDateRange() {
    const startDate = document.getElementById('startDate').value;
    const endDate = document.getElementById('endDate').value;

    if (!startDate || !endDate) {
        alert('请选择开始日期和结束日期');
        return;
    }

    if (startDate > endDate) {
        alert('开始日期不能晚于结束日期');
        return;
    }

    const confirmation = confirm(`确定要删除 ${startDate} 到 ${endDate} 期间的所有数据吗？\n\n此操作不可撤销！`);

    if (confirmation) {
        fetch('/db_admin/delete_by_date_range', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                start_date: startDate,
                end_date: endDate
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                loadRecords(); // 重新加载数据
                alert(`成功删除了 ${data.deleted_count} 条记录`);
                // 清空日期选择器
                document.getElementById('startDate').value = '';
                document.getElementById('endDate').value = '';
            } else {
                alert('删除失败: ' + data.error);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('删除时发生错误');
        });
    }
}

// 清空整个数据库
function confirmClearDatabase() {
    const confirmation = prompt('此操作将删除整个数据库文件！\n请输入 "DELETE DATABASE" 确认操作：');

    if (confirmation === 'DELETE DATABASE') {
        fetch('/db_admin/clear_database', {
            method: 'POST'
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // 隐藏数据表格
                document.getElementById('dataTableContainer').style.display = 'none';
                alert('数据库已完全清空');
                // 刷新页面以更新统计信息
                window.location.reload();
            } else {
                alert('清空数据库失败: ' + data.error);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('清空数据库时发生错误');
        });
    } else if (confirmation !== null) {
        alert('确认文本不正确，操作已取消');
    }
}

// 页面加载完成后的初始化
document.addEventListener('DOMContentLoaded', function() {
    // 全选复选框事件
    document.getElementById('selectAllCheckbox').addEventListener('change', function() {
        if (this.checked) {
            selectAll();
        } else {
            selectNone();
        }
    });
});
