document.addEventListener('DOMContentLoaded', function() {
    const queryInput = document.getElementById('ai-query');
    const queryBtn = document.getElementById('query-btn');
    const resultsContainer = document.getElementById('results-container');
    const chartContainer = document.getElementById('chart-container');
    const aiInsights = document.getElementById('ai-insights');
    const chartTitle = document.getElementById('chart-title');
    const loadingOverlay = document.getElementById('loading-overlay');
    const visualizationContainer = document.getElementById('visualization-container');
    const toggleViewBtn = document.getElementById('toggle-view');
    let dataTable = null;
    let currentData = null;
    let currentConfig = null;
    let currentModel = 'deepseek-chat'; // 默认使用deepseek-chat模型
    let viewMode = 'insights'; // 默认显示洞察视图
    
    // 初始化移动端触摸支持
    initTouchEvents();
    
    // 初始化默认模型
    initDefaultModel();
    
    // 等待DOM完全加载后再初始化图表
    setTimeout(function() {
        // 创建初始占位图表，避免未加载数据时显示奇怪的图形
        initializePlaceholderChart();
    }, 200);
    
    // 添加模型选择器事件监听
    const modelSelect = document.getElementById('model-select');
    if (modelSelect) {
        // 设置初始选择值为deepseek-chat
        modelSelect.value = 'deepseek-chat';
        
        modelSelect.addEventListener('change', function() {
            currentModel = this.value;
            localStorage.setItem('preferredModel', currentModel);
            console.log('已切换模型为: ' + currentModel);
        });
    }
    
    // 注册快捷查询按钮事件
    document.querySelectorAll('.quick-query').forEach(btn => {
        btn.addEventListener('click', function() {
            queryInput.value = this.textContent;
            processQuery();
        });
    });
    
    // 查询按钮事件
    queryBtn.addEventListener('click', processQuery);
    
    // 回车键触发查询
    queryInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            processQuery();
        }
    });
    
    // 切换视图按钮事件
    if (toggleViewBtn) {
        toggleViewBtn.addEventListener('click', function() {
            toggleView();
        });
    }
    
    // 切换视图函数
    function toggleView() {
        if (viewMode === 'insights') {
            // 切换到可视化视图
            viewMode = 'visualization';
            visualizationContainer.style.display = 'block';
            toggleViewBtn.textContent = '显示纯洞察';
            toggleViewBtn.classList.remove('bg-indigo-100', 'text-indigo-700');
            toggleViewBtn.classList.add('bg-gray-100', 'text-gray-700');
        } else {
            // 切换到洞察视图
            viewMode = 'insights';
            visualizationContainer.style.display = 'none';
            toggleViewBtn.textContent = '显示图表';
            toggleViewBtn.classList.remove('bg-gray-100', 'text-gray-700');
            toggleViewBtn.classList.add('bg-indigo-100', 'text-indigo-700');
        }
    }
    
    // 导出洞察为文本
    document.getElementById('export-insights').addEventListener('click', function() {
        if (!aiInsights.textContent) {
            alert('没有可导出的洞察');
            return;
        }
        
        try {
            // 创建一个Blob对象
            const blob = new Blob([aiInsights.innerText], {type: 'text/plain'});
            
            // 创建下载链接
            const link = document.createElement('a');
            link.download = `数据洞察_${new Date().toLocaleDateString()}.txt`;
            link.href = URL.createObjectURL(blob);
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        } catch (error) {
            console.error('导出洞察失败:', error);
            alert('导出洞察失败，请稍后再试');
        }
    });
    
    // 切换图表类型
    document.getElementById('switch-chart').addEventListener('click', function() {
        if (!currentData || !currentConfig) return;
        
        // 定义可用的图表类型
        const chartTypes = ['bar', 'line', 'pie', 'heatmap', 'combo'];
        
        // 获取当前图表类型的索引
        const currentIndex = chartTypes.indexOf(currentConfig.chart_type);
        
        // 计算下一个图表类型的索引（循环）
        const nextIndex = (currentIndex + 1) % chartTypes.length;
        
        // 获取下一个图表类型
        const nextChartType = chartTypes[nextIndex];
        
        // 如果当前有图表实例，销毁它
        if (chartContainer.echart) {
            chartContainer.echart.dispose();
            chartContainer.echart = null;
        }
        
        // 更新当前配置的图表类型
        currentConfig.chart_type = nextChartType;
        
        // 重新渲染图表
        renderChart(currentConfig, currentData);
        
        // 更新图表类型标识
        updateChartTypeBadge(nextChartType);
    });
    
    // 导出图表为图片
    function exportChart() {
        if (!chartContainer.echart) {
            alert('没有可导出的图表');
            return;
        }
        
        try {
            // 获取当前图表的数据URL
            const dataURL = chartContainer.echart.getDataURL({
                type: 'png',
                pixelRatio: 2,
                backgroundColor: '#fff'
            });
            
            // 创建下载链接
            const link = document.createElement('a');
            link.download = `${currentConfig.title || '图表'}.png`;
            link.href = dataURL;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        } catch (error) {
            console.error('导出图表失败:', error);
            alert('导出图表失败，请稍后再试');
        }
    }
    
    // 导出图表按钮事件监听
    document.getElementById('export-chart').addEventListener('click', exportChart);
    
    // 处理查询
    function processQuery() {
        const query = queryInput.value.trim();
        if (!query) return;
        
        // 显示加载状态
        showLoading();
        
        // 构建请求参数
        const params = new URLSearchParams({
            'query': query
        });
        
        // 如果有选择模型，添加到请求参数
        if (currentModel) {
            params.append('model', currentModel);
        }
        
        // 发送查询到后端
        fetch('/api/query', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: params
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('网络请求失败');
            }
            return response.json();
        })
        .then(data => {
            console.log('API响应数据:', data);
            
            if (data.error) {
                alert('查询错误: ' + data.error);
                return;
            }
            
            // 保存当前数据和配置
            currentData = data.data;
            currentConfig = data.visualization;
            
            // 显示结果容器
            resultsContainer.style.display = 'grid';
            
            // 渲染图表
            renderChart(data.visualization, data.data);
            
            // 更新图表标题
            chartTitle.textContent = data.visualization.title || '数据可视化';
            
            // 渲染AI洞察
            renderInsights(data.insights);
            
            // 渲染数据表格
            renderDataTable(data.data);
            
            // 设置默认视图模式
            if (viewMode === 'insights') {
                visualizationContainer.style.display = 'none';
                toggleViewBtn.textContent = '显示图表';
                toggleViewBtn.classList.remove('bg-gray-100', 'text-gray-700');
                toggleViewBtn.classList.add('bg-indigo-100', 'text-indigo-700');
            } else {
                visualizationContainer.style.display = 'block';
                toggleViewBtn.textContent = '显示纯洞察';
                toggleViewBtn.classList.remove('bg-indigo-100', 'text-indigo-700');
                toggleViewBtn.classList.add('bg-gray-100', 'text-gray-700');
            }
            
            // 滚动到结果区域
            resultsContainer.scrollIntoView({behavior: 'smooth'});
        })
        .catch(error => {
            console.error('Error:', error);
            alert('查询处理过程中发生错误，请重试');
        })
        .finally(() => {
            hideLoading();
        });
    }
    
    // 渲染图表
    function renderChart(config, data) {
        console.log('开始渲染图表，配置:', JSON.stringify(config));
        console.log('数据样本:', data.length > 0 ? JSON.stringify(data[0]) : '无数据');
        
        // 清空图表容器
        chartContainer.innerHTML = '';
        
        // 检测是否为移动设备
        const isMobile = window.innerWidth < 640;
        
        // 确保容器尺寸已设置
        chartContainer.style.width = '100%';
        chartContainer.style.height = isMobile ? '300px' : '400px';
        console.log('图表容器尺寸设置为:', chartContainer.style.width, 'x', chartContainer.style.height);
        
        // 确保数据有效
        if (!data || !Array.isArray(data) || data.length === 0) {
            console.error('无效数据，无法渲染图表');
            chartContainer.innerHTML = '<div class="flex items-center justify-center h-full text-gray-500">没有可显示的数据</div>';
            return;
        }
        
        console.log('图表类型:', config.chart_type);
        console.log('X轴字段:', config.x_field);
        console.log('Y轴字段:', config.y_field);
        
        switch(config.chart_type) {
            case 'bar':
                console.log('渲染条形图');
                renderBarChart(config, data, isMobile);
                break;
            case 'line':
                console.log('渲染折线图');
                renderLineChart(config, data, isMobile);
                break;
            case 'pie':
                console.log('渲染饼图');
                renderPieChart(config, data, isMobile);
                break;
            case 'scatter':
                console.log('渲染散点图');
                renderScatterChart(config, data, isMobile);
                break;
            case 'combo':
                console.log('渲染组合图');
                renderComboChart(config, data, isMobile);
                break;
            case 'heatmap':
                console.log('渲染热力图');
                renderHeatmap(config, data, isMobile);
                break;
            default:
                console.log('未知图表类型，使用默认条形图');
                renderBarChart(config, data, isMobile);
        }
        
        // 更新图表类型标识
        updateChartTypeBadge(config.chart_type);
        console.log('图表渲染完成');
    }
    
    // 渲染条形图
    function renderBarChart(config, data, isMobile) {
        if (!data || data.length === 0) return;
        
        // 初始化图表
        const myChart = echarts.init(chartContainer);
        chartContainer.echart = myChart;
        
        // 处理X轴和Y轴字段
        const xField = config.x_field;
        let yField = config.y_field;
        
        // 处理 yField 可能是数组的情况
        let seriesData = [];
        if (Array.isArray(yField)) {
            // 如果是数组，为每个y字段创建一个系列
            seriesData = yField.map(field => {
                return {
                    name: getFieldDisplayName(field),
                    type: 'bar',
                    data: data.map(item => item[field] || 0)
                };
            });
        } else {
            // 如果不是数组，创建单一系列
            seriesData = [{
                name: getFieldDisplayName(yField),
                type: 'bar',
                data: data.map(item => item[yField] || 0)
            }];
        }
        
        // 准备X轴数据
        const xAxisData = data.map(item => item[xField]);
        
        // 图表配置
        const option = {
            tooltip: {
                trigger: 'axis',
                axisPointer: {
                    type: 'shadow'
                }
            },
            legend: {
                data: seriesData.map(series => series.name),
                top: isMobile ? 0 : 10,
                left: isMobile ? 'center' : 'right',
                textStyle: {
                    fontSize: isMobile ? 10 : 12
                },
                itemWidth: isMobile ? 12 : 16,
                itemHeight: isMobile ? 8 : 12
            },
            grid: {
                left: '3%',
                right: '4%',
                bottom: '3%',
                containLabel: true
            },
            xAxis: {
                type: 'category',
                data: xAxisData,
                axisLabel: {
                    rotate: xAxisData.length > 5 ? 45 : 0,
                    fontSize: isMobile ? 10 : 12
                }
            },
            yAxis: {
                type: 'value',
                name: config.y_label,
                nameTextStyle: {
                    fontSize: isMobile ? 10 : 12
                },
                axisLabel: {
                    formatter: function(value) {
                        return value >= 1000 ? (value / 1000).toFixed(1) + 'k' : value;
                    },
                    fontSize: isMobile ? 10 : 12
                }
            },
            series: seriesData
        };
        
        // 设置图表选项
        myChart.setOption(option);
        
        // 窗口大小变化时重新调整图表大小
        window.addEventListener('resize', function() {
            myChart.resize();
        });
    }
    
    // 渲染折线图
    function renderLineChart(config, data, isMobile) {
        if (!data || data.length === 0) return;
        
        // 初始化图表
        const myChart = echarts.init(chartContainer);
        chartContainer.echart = myChart;
        
        // 处理X轴和Y轴字段
        const xField = config.x_field;
        let yField = config.y_field;
        
        // 处理 yField 可能是数组的情况
        let seriesData = [];
        if (Array.isArray(yField)) {
            // 如果是数组，为每个y字段创建一个系列
            seriesData = yField.map(field => {
                return {
                    name: getFieldDisplayName(field),
                    type: 'line',
                    smooth: true,
                    data: data.map(item => item[field] || 0),
                    symbolSize: isMobile ? 4 : 6
                };
            });
        } else {
            // 如果不是数组，创建单一系列
            seriesData = [{
                name: getFieldDisplayName(yField),
                type: 'line',
                smooth: true,
                data: data.map(item => item[yField] || 0),
                symbolSize: isMobile ? 4 : 6
            }];
        }
        
        // 准备X轴数据
        const xAxisData = data.map(item => item[xField]);
        
        // 图表配置
        const option = {
            tooltip: {
                trigger: 'axis'
            },
            legend: {
                data: seriesData.map(series => series.name),
                top: isMobile ? 0 : 10,
                left: isMobile ? 'center' : 'right',
                textStyle: {
                    fontSize: isMobile ? 10 : 12
                },
                itemWidth: isMobile ? 12 : 16,
                itemHeight: isMobile ? 8 : 12
            },
            grid: {
                left: '3%',
                right: '4%',
                bottom: '3%',
                containLabel: true
            },
            xAxis: {
                type: 'category',
                boundaryGap: false,
                data: xAxisData,
                axisLabel: {
                    rotate: xAxisData.length > 5 ? 45 : 0,
                    fontSize: isMobile ? 10 : 12
                }
            },
            yAxis: {
                type: 'value',
                name: config.y_label,
                nameTextStyle: {
                    fontSize: isMobile ? 10 : 12
                },
                axisLabel: {
                    formatter: function(value) {
                        return value >= 1000 ? (value / 1000).toFixed(1) + 'k' : value;
                    },
                    fontSize: isMobile ? 10 : 12
                }
            },
            series: seriesData
        };
        
        // 设置图表选项
        myChart.setOption(option);
        
        // 窗口大小变化时重新调整图表大小
        window.addEventListener('resize', function() {
            myChart.resize();
        });
    }
    
    // 渲染饼图
    function renderPieChart(config, data, isMobile) {
        if (!data || data.length === 0) return;
        
        // 初始化图表
        const myChart = echarts.init(chartContainer);
        chartContainer.echart = myChart;
        
        // 处理X轴和Y轴字段
        const xField = config.x_field; // 类别字段
        let yField = config.y_field; // 数值字段
        
        // 确保有数值字段可用
        let primaryYField = Array.isArray(yField) ? yField[0] : yField;
        
        // 准备饼图数据
        const pieData = data.map(item => ({
            name: item[xField],
            value: item[primaryYField] || 0
        }));
        
        // 图表配置
        const option = {
            tooltip: {
                trigger: 'item',
                formatter: '{a} <br/>{b}: {c} ({d}%)'
            },
            legend: {
                orient: 'vertical',
                left: isMobile ? 'center' : 'left',
                top: isMobile ? 'bottom' : 'middle',
                type: isMobile ? 'scroll' : 'plain',
                textStyle: {
                    fontSize: isMobile ? 10 : 12
                },
                pageIconSize: isMobile ? 10 : 12,
                pageTextStyle: {
                    fontSize: isMobile ? 10 : 12
                }
            },
            series: [
                {
                    name: getFieldDisplayName(primaryYField),
                    type: 'pie',
                    radius: ['40%', '70%'],
                    avoidLabelOverlap: false,
                    center: ['50%', isMobile ? '40%' : '50%'],
                    itemStyle: {
                        borderRadius: 4,
                        borderColor: '#fff',
                        borderWidth: 2
                    },
                    label: {
                        show: false,
                        position: 'center'
                    },
                    emphasis: {
                        label: {
                            show: true,
                            fontSize: isMobile ? '14' : '18',
                            fontWeight: 'bold'
                        }
                    },
                    labelLine: {
                        show: false
                    },
                    data: pieData
                }
            ]
        };
        
        // 设置图表选项
        myChart.setOption(option);
        
        // 窗口大小变化时重新调整图表大小
        window.addEventListener('resize', function() {
            myChart.resize();
        });
        
        // 处理多个Y字段的情况
        if (Array.isArray(yField) && yField.length > 1) {
            // 添加切换按钮
            const switchContainer = document.createElement('div');
            switchContainer.className = 'absolute top-2 right-2 flex space-x-2';
            
            yField.forEach((field, index) => {
                const button = document.createElement('button');
                button.className = 'px-2 py-1 text-xs rounded ' + 
                    (index === 0 ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-700');
                button.textContent = getFieldDisplayName(field);
                
                button.addEventListener('click', function() {
                    // 更新所有按钮样式
                    switchContainer.querySelectorAll('button').forEach(btn => {
                        btn.className = 'px-2 py-1 text-xs rounded bg-gray-200 text-gray-700';
                    });
                    this.className = 'px-2 py-1 text-xs rounded bg-blue-600 text-white';
                    
                    // 更新图表数据
                    const newPieData = data.map(item => ({
                        name: item[xField],
                        value: item[field] || 0
                    }));
                    
                    myChart.setOption({
                        series: [{
                            name: getFieldDisplayName(field),
                            data: newPieData
                        }]
                    });
                });
                
                switchContainer.appendChild(button);
            });
            
            chartContainer.appendChild(switchContainer);
        }
    }
    
    // 渲染散点图
    function renderScatterChart(config, data, isMobile) {
        const xValues = data.map(item => item[config.x_field]);
        const yValues = data.map(item => item[config.y_field]);
        
        const trace = {
            x: xValues,
            y: yValues,
            type: 'scatter',
            mode: 'markers',
            marker: {
                color: 'rgba(76, 110, 245, 0.8)',
                size: 10,
                opacity: 0.7
            }
        };
        
        const layout = {
            title: config.title,
            font: {
                family: 'Inter, sans-serif'
            },
            xaxis: {
                title: config.x_label,
                automargin: true
            },
            yaxis: {
                title: config.y_label,
                automargin: true
            },
            autosize: true,
            margin: {
                l: 50,
                r: 50,
                b: 80,
                t: 50,
                pad: 4
            }
        };
        
        Plotly.newPlot(chartContainer, [trace], layout, {
            responsive: true,
            displayModeBar: !isMobile,
            modeBarButtonsToRemove: ['lasso2d', 'select2d']
        });
    }
    
    // 渲染组合图表
    function renderComboChart(config, data, isMobile) {
        // 清空容器
        chartContainer.innerHTML = '';
        
        // 初始化ECharts实例
        const myChart = echarts.init(chartContainer);
        
        // 提取x轴数据
        const xValues = [...new Set(data.map(item => item[config.x_field]))].sort();
        
        // 获取所有y轴指标
        const metrics = config.metrics || [];
        if (metrics.length < 2) {
            chartContainer.innerHTML = '<div class="text-center p-4 text-red-500">组合图表需要至少两个指标</div>';
            return;
        }
        
        // 准备系列数据
        const series = [];
        const colors = ['#4F46E5', '#10B981', '#F59E0B', '#EF4444', '#6366F1'];
        
        // 第一个指标作为柱状图
        const barData = [];
        xValues.forEach(x => {
            const matchingItems = data.filter(item => item[config.x_field] === x);
            if (matchingItems.length > 0) {
                barData.push(matchingItems[0][metrics[0]] || 0);
            } else {
                barData.push(0);
            }
        });
        
        series.push({
            name: metrics[0],
            type: 'bar',
            data: barData,
            itemStyle: {
                color: colors[0]
            },
            label: {
                show: true,
                position: 'top',
                formatter: '{c}'
            }
        });
        
        // 其余指标作为折线图
        for (let i = 1; i < metrics.length; i++) {
            const lineData = [];
            xValues.forEach(x => {
                const matchingItems = data.filter(item => item[config.x_field] === x);
                if (matchingItems.length > 0) {
                    lineData.push(matchingItems[0][metrics[i]] || 0);
                } else {
                    lineData.push(0);
                }
            });
            
            series.push({
                name: metrics[i],
                type: 'line',
                yAxisIndex: i - 1,
                data: lineData,
                smooth: true,
                symbol: 'circle',
                symbolSize: 8,
                itemStyle: {
                    color: colors[i % colors.length]
                },
                lineStyle: {
                    width: 3,
                    color: colors[i % colors.length]
                },
                label: {
                    show: true,
                    position: 'top',
                    formatter: '{c}'
                }
            });
        }
        
        // 准备多个y轴
        const yAxis = [{
            type: 'value',
            name: metrics[0],
            position: 'left',
            nameLocation: 'middle',
            nameGap: 50,
            axisLine: {
                show: true,
                lineStyle: {
                    color: colors[0]
                }
            },
            axisLabel: {
                color: colors[0]
            }
        }];
        
        // 为每个额外的指标添加一个y轴
        for (let i = 1; i < metrics.length; i++) {
            yAxis.push({
                type: 'value',
                name: metrics[i],
                position: 'right',
                nameLocation: 'middle',
                nameGap: 50 + (i - 1) * 60,
                offset: (i - 1) * 60,
                axisLine: {
                    show: true,
                    lineStyle: {
                        color: colors[i % colors.length]
                    }
                },
                axisLabel: {
                    color: colors[i % colors.length]
                }
            });
        }
        
        // 准备ECharts配置
        const option = {
            title: {
                text: config.title,
                left: 'center',
                textStyle: {
                    fontSize: isMobile ? 14 : 16,
                    fontFamily: 'Inter, sans-serif'
                }
            },
            tooltip: {
                trigger: 'axis',
                axisPointer: {
                    type: 'cross'
                },
                formatter: function(params) {
                    let tooltip = params[0].name + '<br/>';
                    params.forEach(param => {
                        tooltip += `${param.seriesName}: ${param.value.toFixed(2)}<br/>`;
                    });
                    return tooltip;
                }
            },
            legend: {
                data: metrics,
                bottom: 10,
                left: 'center',
                type: isMobile ? 'scroll' : 'plain'
            },
            grid: {
                top: isMobile ? 60 : 70,
                bottom: isMobile ? 80 : 60,
                left: isMobile ? 60 : 80,
                right: isMobile ? 80 : 100,
                containLabel: true
            },
            xAxis: {
                type: 'category',
                data: xValues,
                name: config.x_label || config.x_field,
                nameLocation: 'middle',
                nameGap: 30,
                axisLabel: {
                    rotate: isMobile ? 45 : 0,
                    interval: 0
                }
            },
            yAxis: yAxis,
            series: series
        };
        
        // 设置ECharts实例的选项并渲染
        myChart.setOption(option);
        
        // 响应窗口大小变化
        window.addEventListener('resize', function() {
            myChart.resize();
        });
        
        // 保存当前图表实例以便导出
        chartContainer.echart = myChart;
    }
    
    // 渲染热力图
    function renderHeatmap(config, data, isMobile) {
        // 提取唯一的x和y值
        const xValues = [...new Set(data.map(item => item[config.x_field]))].sort();
        const yValues = [...new Set(data.map(item => item[config.y_field]))].sort();
        
        // 创建热力图数据
        const zValues = Array(yValues.length).fill().map(() => Array(xValues.length).fill(0));
        
        // 填充热力图数据
        data.forEach(item => {
            const xIndex = xValues.indexOf(item[config.x_field]);
            const yIndex = yValues.indexOf(item[config.y_field]);
            if (xIndex !== -1 && yIndex !== -1) {
                zValues[yIndex][xIndex] = parseFloat(item[config.z_field]) || 0;
            }
        });
        
        // 清空容器
        chartContainer.innerHTML = '';
        
        // 初始化ECharts实例
        const myChart = echarts.init(chartContainer);
        
        // 准备ECharts配置
        const option = {
            title: {
                text: config.title,
                left: 'center',
                textStyle: {
                    fontSize: isMobile ? 14 : 16,
                    fontFamily: 'Inter, sans-serif'
                }
            },
            tooltip: {
                position: 'top',
                formatter: function(params) {
                    const value = params.value;
                    return `${xValues[value[0]]}, ${yValues[value[1]]}<br>${config.z_label || config.z_field}: ${value[2].toFixed(2)}`;
                }
            },
            grid: {
                top: isMobile ? 60 : 70,
                bottom: isMobile ? 80 : 60,
                left: isMobile ? 100 : 120,
                right: isMobile ? 20 : 30,
                containLabel: true
            },
            xAxis: {
                type: 'category',
                data: xValues,
                name: config.x_label || config.x_field,
                nameLocation: 'middle',
                nameGap: 30,
                axisLabel: {
                    rotate: isMobile ? 45 : 0,
                    interval: 0
                },
                splitArea: {
                    show: true
                }
            },
            yAxis: {
                type: 'category',
                data: yValues,
                name: config.y_label || config.y_field,
                nameLocation: 'middle',
                nameGap: 70,
                splitArea: {
                    show: true
                }
            },
            visualMap: {
                min: 0,
                max: Math.max(...zValues.flat()),
                calculable: true,
                orient: 'horizontal',
                left: 'center',
                bottom: '0',
                inRange: {
                    color: [
                        '#e0f7fa', '#b2ebf2', '#80deea', 
                        '#4dd0e1', '#26c6da', '#00bcd4', 
                        '#00acc1', '#0097a7', '#00838f'
                    ]
                }
            },
            series: [{
                name: config.z_label || config.z_field,
                type: 'heatmap',
                data: zValues.map((row, yIndex) => {
                    return row.map((value, xIndex) => {
                        return [xIndex, yIndex, value];
                    });
                }).flat(),
                label: {
                    show: true,
                    formatter: function(params) {
                        return params.value[2].toFixed(1);
                    }
                },
                emphasis: {
                    itemStyle: {
                        shadowBlur: 10,
                        shadowColor: 'rgba(0, 0, 0, 0.5)'
                    }
                }
            }]
        };
        
        // 设置ECharts实例的选项并渲染
        myChart.setOption(option);
        
        // 响应窗口大小变化
        window.addEventListener('resize', function() {
            myChart.resize();
        });
        
        // 保存当前图表实例以便导出
        chartContainer.echart = myChart;
    }
    
    // 渲染AI洞察
    function renderInsights(insights) {
        if (!insights) {
            aiInsights.innerHTML = '<p class="text-gray-500">暂无AI分析内容</p>';
            return;
        }
        
        // 检查insights是对象还是字符串
        if (typeof insights === 'object') {
            // 构建格式化的HTML
            let html = '<div class="space-y-4">';
            
            // 添加总结
            if (insights.summary) {
                html += `<div class="mb-4">
                    <h3 class="text-lg font-medium text-gray-900 mb-2">总体分析</h3>
                    <p class="text-gray-700">${insights.summary}</p>
                </div>`;
            }
            
            // 添加关键发现
            if (insights.key_findings && insights.key_findings.length > 0) {
                html += `<div class="mb-4">
                    <h3 class="text-lg font-medium text-gray-900 mb-2">关键发现</h3>
                    <ul class="list-disc pl-5 space-y-1">`;
                
                insights.key_findings.forEach(finding => {
                    html += `<li class="text-gray-700">${finding}</li>`;
                });
                
                html += `</ul></div>`;
            }
            
            // 添加异常点
            if (insights.anomalies && insights.anomalies.length > 0) {
                html += `<div class="mb-4">
                    <h3 class="text-lg font-medium text-orange-700 mb-2">异常点</h3>
                    <ul class="list-disc pl-5 space-y-1">`;
                
                insights.anomalies.forEach(anomaly => {
                    html += `<li class="text-orange-600">${anomaly}</li>`;
                });
                
                html += `</ul></div>`;
            }
            
            // 添加建议
            if (insights.recommendations && insights.recommendations.length > 0) {
                html += `<div class="mb-4">
                    <h3 class="text-lg font-medium text-indigo-700 mb-2">建议</h3>
                    <ul class="list-disc pl-5 space-y-1">`;
                
                insights.recommendations.forEach(recommendation => {
                    html += `<li class="text-indigo-600">${recommendation}</li>`;
                });
                
                html += `</ul></div>`;
            }
            
            // 添加对比信息
            if (insights.comparisons) {
                html += `<div class="mb-4">
                    <h3 class="text-lg font-medium text-gray-900 mb-2">对比分析</h3>
                    <div class="space-y-2">`;
                
                for (const [key, value] of Object.entries(insights.comparisons)) {
                    if (value && typeof value === 'object') {
                        // 处理嵌套对象，比如growth_rates
                        html += `<div class="mb-2">
                            <h4 class="text-md font-medium text-gray-800">${getComparisonTitle(key)}</h4>
                            <ul class="list-disc pl-5">`;
                        
                        for (const [subKey, subValue] of Object.entries(value)) {
                            if (subValue) {
                                html += `<li class="text-gray-700">${getComparisonTitle(subKey)}: ${subValue}</li>`;
                            }
                        }
                        
                        html += `</ul></div>`;
                    } else if (value) {
                        // 处理简单字符串值
                        html += `<p class="text-gray-700"><span class="font-medium">${getComparisonTitle(key)}:</span> ${value}</p>`;
                    }
                }
                
                html += `</div></div>`;
            }
            
            html += '</div>';
            aiInsights.innerHTML = html;
        } else {
            // 如果是字符串，直接显示
        aiInsights.innerHTML = `<div class="whitespace-pre-line text-base leading-relaxed">${insights}</div>`;
        }
    }
    
    // 获取对比分析的标题
    function getComparisonTitle(key) {
        const titles = {
            'channel_comparison': '渠道对比',
            'time_comparison': '时间对比',
            'growth_rates': '增长率',
            'revenue_growth': '收入增长',
            'room_nights_growth': '间夜增长'
        };
        return titles[key] || key;
    }
    
    // 渲染数据表格
    function renderDataTable(data) {
        const tableWrapper = document.getElementById('data-table-wrapper');
        if (!tableWrapper) {
            console.error('数据表格容器 "data-table-wrapper" 未找到');
            return;
        }

        if (!data || data.length === 0) {
            tableWrapper.style.display = 'none';
            return;
        }
        
        // 显示表格区域
        tableWrapper.style.display = 'block';
        
        // 如果已有表格实例，销毁它
        if (dataTable) {
            dataTable.destroy();
        }
        
        const tableElement = document.getElementById('data-table');
        if (!tableElement) {
            console.error('数据表格 "data-table" 未找到');
            return;
        }
        
        // 获取列名
        const columns = Object.keys(data[0]).map(key => {
            let columnDef = {
                title: key.charAt(0).toUpperCase() + key.slice(1).replace(/_/g, ' '),
                data: key
            };
            
            // 为百分比列添加格式化
            if (key === 'percentage') {
                columnDef.render = function(data, type, row) {
                    if (type === 'display') {
                        return (data * 100).toFixed(2) + '%';
                    }
                    return data;
                };
            }
            
            // 为收入列添加格式化
            if (key === 'revenue' || key === 'avg_price') {
                columnDef.render = function(data, type, row) {
                    if (type === 'display') {
                        return parseFloat(data).toLocaleString('zh-CN', {
                            minimumFractionDigits: 2,
                            maximumFractionDigits: 2
                        }) + ' 元';
                    }
                    return data;
                };
            }
            
            return columnDef;
        });
        
        // 检测是否为移动设备
        const isMobile = window.innerWidth < 640;
        
        // 创建DataTable实例
        dataTable = new DataTable(tableElement, {
            data: data,
            columns: columns,
            pageLength: isMobile ? 5 : 10,
            responsive: true,
            language: {
                paginate: {
                    previous: '上一页',
                    next: '下一页'
                },
                info: "显示 _START_ 到 _END_ 条，共 _TOTAL_ 条数据",
                infoEmpty: "没有数据",
                emptyTable: "没有可用数据",
                search: "搜索:",
                lengthMenu: "显示 _MENU_ 条数据",
                zeroRecords: "没有匹配的记录"
            },
            dom: isMobile ? 'ftip' : 'Bfrtip',
            buttons: isMobile ? [] : ['copy', 'csv', 'excel']
        });
    }
    
    // 移动端触摸事件初始化
    function initTouchEvents() {
        // 为快捷查询容器添加横向滚动支持
        const quickQueriesContainer = document.querySelector('.quick-queries-container');
        if (quickQueriesContainer && window.innerWidth < 640) {
            let isScrolling = false;
            let startX, scrollLeft;
            
            quickQueriesContainer.addEventListener('touchstart', (e) => {
                isScrolling = true;
                startX = e.touches[0].pageX - quickQueriesContainer.offsetLeft;
                scrollLeft = quickQueriesContainer.scrollLeft;
            });
            
            quickQueriesContainer.addEventListener('touchend', () => {
                isScrolling = false;
            });
            
            quickQueriesContainer.addEventListener('touchmove', (e) => {
                if (!isScrolling) return;
                e.preventDefault();
                const x = e.touches[0].pageX - quickQueriesContainer.offsetLeft;
                const walk = (x - startX) * 2;
                quickQueriesContainer.scrollLeft = scrollLeft - walk;
            });
        }
    }
    
    // 初始化默认模型
    function initDefaultModel() {
        // 强制重置localStorage中的模型设置为deepseek-chat
        localStorage.setItem('preferredModel', 'deepseek-chat');
        currentModel = 'deepseek-chat';
        console.log('已设置默认模型为: deepseek-chat');
    }
    
    // 处理窗口大小变化
    window.addEventListener('resize', function() {
        if (chartContainer.echart) {
            chartContainer.echart.resize();
        }
    });
    
    // 显示加载状态
    function showLoading() {
        loadingOverlay.style.display = 'block';
        // 启动进度条动画
        const progressBar = document.getElementById('progress-bar');
        progressBar.style.width = '0%';
        progressBar.classList.add('progress-animate');
        
        // 禁用查询按钮
        queryBtn.disabled = true;
        queryBtn.classList.add('opacity-50');
        queryBtn.textContent = '分析中...';
    }
    
    // 隐藏加载状态
    function hideLoading() {
        loadingOverlay.style.display = 'none';
        // 停止进度条动画
        const progressBar = document.getElementById('progress-bar');
        progressBar.classList.remove('progress-animate');
        progressBar.style.width = '100%';
        
        // 恢复查询按钮
        queryBtn.disabled = false;
        queryBtn.classList.remove('opacity-50');
        queryBtn.textContent = '分析';
        
        // 延迟一会儿后隐藏加载状态
        setTimeout(() => {
            loadingOverlay.style.display = 'none';
            progressBar.style.width = '0%';
        }, 500);
    }
    
    // 更新图表类型标识
    function updateChartTypeBadge(chartType) {
        const badge = document.getElementById('chart-type-badge');
        if (!badge) return;
        
        // 清除所有类名
        badge.className = 'chart-type-badge';
        
        // 设置图表类型文本
        let typeName = '';
        switch (chartType) {
            case 'bar':
                typeName = '条形图';
                break;
            case 'line':
                typeName = '折线图';
                break;
            case 'pie':
                typeName = '饼图';
                break;
            case 'heatmap':
                typeName = '热力图';
                break;
            default:
                typeName = '图表';
        }
        
        badge.textContent = typeName;
        
        // 添加特定图表类型的类名
        if (chartType === 'heatmap') {
            badge.classList.add('heatmap-chart');
        }
    }
    
    // 初始化一个占位图表
    function initializePlaceholderChart() {
        try {
            console.log("初始化占位图表");
            if (typeof echarts === 'undefined') {
                console.error("ECharts未加载");
                return;
            }
            
            const container = document.getElementById('chart-container');
            if (!container) {
                console.error("图表容器未找到");
                return;
            }
            
            console.log("容器尺寸:", container.offsetWidth, "x", container.offsetHeight);
            
            // 确保容器有明确的尺寸
            container.style.width = '100%';
            container.style.height = '400px';
            
            // 如果已有图表实例，先销毁
            if (container.echart) {
                container.echart.dispose();
            }
            
            // 初始化新的图表实例
            try {
                console.log("创建ECharts实例");
                const myChart = echarts.init(container);
                console.log("ECharts实例创建成功");
                
                const option = {
                    title: {
                        text: '等待数据输入',
                        left: 'center',
                        top: 'center'
                    },
                    tooltip: {},
                    xAxis: {
                        data: ['请输入查询']
                    },
                    yAxis: {},
                    series: [{
                        name: '示例',
                        type: 'bar',
                        data: [0],
                        itemStyle: {
                            color: '#6366f1'
                        }
                    }]
                };
                
                console.log("设置图表选项");
                myChart.setOption(option);
                console.log("图表选项设置成功");
                
                container.echart = myChart;
                console.log("占位图表初始化完成");
            } catch (chartError) {
                console.error("创建图表实例失败:", chartError);
            }
        } catch (error) {
            console.error("初始化占位图表失败:", error);
        }
    }
    
    // 为新增的辅助函数
    function getFieldDisplayName(field) {
        const fieldLabels = {
            'revenue': '收入',
            'room_nights': '间夜数',
            'avg_price': '平均房价',
            'occupancy_rate': '出租率',
            'total_revenue': '总收入',
            'total_room_nights': '总间夜数'
        };
        
        return fieldLabels[field] || field;
    }
    
    // 打印报表功能
    const printReportBtn = document.getElementById('print-report');
    if (printReportBtn) {
        printReportBtn.addEventListener('click', function() {
            if (!resultsContainer || resultsContainer.style.display === 'none') {
                alert('请先进行数据分析，生成报表内容');
                return;
            }
            
            // 添加时间戳
            const currentDate = new Date();
            const formattedDate = currentDate.toLocaleString('zh-CN', {
                year: 'numeric',
                month: '2-digit',
                day: '2-digit',
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit'
            });
            
            // 设置时间戳属性，用于打印样式表中显示
            resultsContainer.setAttribute('data-timestamp', formattedDate);
            
            // 确保所有内容都可见（包括图表和表格）
            const dataTableWrapper = document.getElementById('data-table-wrapper');
            if (dataTableWrapper) {
                dataTableWrapper.style.display = 'block';
            }
            
            visualizationContainer.style.display = 'block';
            
            // 如果图表存在，确保它已经完全渲染
            if (chartContainer.echart) {
                chartContainer.echart.resize();
            }
            
            // 延迟一下，确保所有内容都已渲染完成
            setTimeout(function() {
                // 调用打印功能
                window.print();
            }, 300);
        });
    }
    
    // 导出PDF功能
    const exportPdfBtn = document.getElementById('export-pdf');
    if (exportPdfBtn) {
        exportPdfBtn.addEventListener('click', function() {
            if (!resultsContainer || resultsContainer.style.display === 'none') {
                alert('请先进行数据分析，生成报表内容');
                return;
            }
            
            // 显示加载状态
            showLoading();
            
            // 添加时间戳
            const currentDate = new Date();
            const formattedDate = currentDate.toLocaleString('zh-CN', {
                year: 'numeric',
                month: '2-digit',
                day: '2-digit',
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit'
            });
            
            // 设置时间戳属性
            resultsContainer.setAttribute('data-timestamp', formattedDate);
            
            // 确保所有内容都可见
            const dataTableWrapper = document.getElementById('data-table-wrapper');
            if (dataTableWrapper) {
                dataTableWrapper.style.display = 'block';
            }
            
            visualizationContainer.style.display = 'block';
            
            // 如果图表存在，确保它已经完全渲染
            if (chartContainer.echart) {
                chartContainer.echart.resize();
            }
            
            // 创建一个临时的报表容器，用于PDF导出
            const reportContainer = document.createElement('div');
            reportContainer.className = 'pdf-report-container';
            
            // 添加报表标题
            const reportTitle = document.createElement('h1');
            reportTitle.textContent = '乐巷酒店数据分析报表';
            reportTitle.style.textAlign = 'center';
            reportTitle.style.marginBottom = '20px';
            reportTitle.style.fontSize = '24px';
            reportTitle.style.borderBottom = '2px solid #000';
            reportTitle.style.paddingBottom = '10px';
            reportContainer.appendChild(reportTitle);
            
            // 复制AI洞察内容
            const insightsClone = aiInsights.cloneNode(true);
            const insightsTitle = document.createElement('h2');
            insightsTitle.textContent = 'AI数据洞察';
            insightsTitle.style.fontSize = '20px';
            insightsTitle.style.marginTop = '20px';
            insightsTitle.style.marginBottom = '10px';
            reportContainer.appendChild(insightsTitle);
            reportContainer.appendChild(insightsClone);
            
            // 如果有图表，添加图表
            if (chartContainer.echart) {
                const chartTitle = document.createElement('h2');
                chartTitle.textContent = '数据可视化';
                chartTitle.style.fontSize = '20px';
                chartTitle.style.marginTop = '20px';
                chartTitle.style.marginBottom = '10px';
                reportContainer.appendChild(chartTitle);
                
                // 获取图表的图像
                const chartImage = document.createElement('img');
                chartImage.src = chartContainer.echart.getDataURL({
                    type: 'png',
                    pixelRatio: 2,
                    backgroundColor: '#fff'
                });
                chartImage.style.width = '100%';
                chartImage.style.maxWidth = '800px';
                chartImage.style.display = 'block';
                chartImage.style.margin = '0 auto';
                reportContainer.appendChild(chartImage);
            }
            
            // 如果有表格数据，添加表格
            if (dataTable) {
                const tableTitle = document.createElement('h2');
                tableTitle.textContent = '详细数据';
                tableTitle.style.fontSize = '20px';
                tableTitle.style.marginTop = '20px';
                tableTitle.style.marginBottom = '10px';
                reportContainer.appendChild(tableTitle);
                
                // 克隆表格
                const tableClone = document.getElementById('data-table').cloneNode(true);
                
                // 应用表格样式
                tableClone.style.width = '100%';
                tableClone.style.borderCollapse = 'collapse';
                tableClone.style.marginTop = '10px';
                
                // 应用表格单元格样式
                const cells = tableClone.querySelectorAll('th, td');
                cells.forEach(cell => {
                    cell.style.border = '1px solid #ddd';
                    cell.style.padding = '8px';
                    cell.style.textAlign = 'left';
                });
                
                // 应用表头样式
                const headers = tableClone.querySelectorAll('th');
                headers.forEach(header => {
                    header.style.backgroundColor = '#f2f2f2';
                    header.style.color = 'black';
                });
                
                reportContainer.appendChild(tableClone);
            }
            
            // 添加时间戳
            const timestamp = document.createElement('p');
            timestamp.textContent = '生成时间: ' + formattedDate;
            timestamp.style.textAlign = 'right';
            timestamp.style.fontSize = '12px';
            timestamp.style.marginTop = '20px';
            timestamp.style.borderTop = '1px solid #ddd';
            timestamp.style.paddingTop = '10px';
            reportContainer.appendChild(timestamp);
            
            // 配置PDF选项
            const options = {
                margin: 10,
                filename: `乐巷酒店数据分析报表_${new Date().toISOString().slice(0, 10)}.pdf`,
                image: { type: 'jpeg', quality: 0.98 },
                html2canvas: { scale: 2, useCORS: true },
                jsPDF: { unit: 'mm', format: 'a4', orientation: 'portrait' }
            };
            
            // 生成PDF
            html2pdf().from(reportContainer).set(options).save().then(() => {
                // 隐藏加载状态
                hideLoading();
            }).catch(error => {
                console.error('导出PDF失败:', error);
                alert('导出PDF失败，请稍后再试');
                hideLoading();
            });
        });
    }
});
