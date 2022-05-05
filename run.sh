#!/bin/bash

# 日志目录
log_dir="/var/log/service/intelligent-assistant"

#导厨技能服务端口
kitchen_rasa_port=18021
#其他技能服务端口
others_rasa_port=18023
#专利技能服务端口
patent_rasa_port=18024


skill(){
  echo "skill list update...."
  su root -c "source venv/bin/activate && python IntelligentAssistant/common/data_update.py"
}

#启动服务方法
start() {
  echo "Please input the start server name：kitchen|patent|others|all"
  read name
  case $name in
  "kitchen")
    echo "$name dialogue service start...."
    su root -c "source venv/bin/activate && cd dialogue/kitchen && rasa run --log-file $log_dir/kitchen_rasa.log -v -p $kitchen_rasa_port --enable-api &"
    ;;

  "patent")
    echo "$name dialogue service start...."
    su root -c "source venv/bin/activate && cd dialogue/patent && rasa run --log-file $log_dir/patent_rasa.log -v -p $patent_rasa_port --enable-api &"
    ;;

  "others")
    echo "$name dialogue service start...."
    su root -c "source venv/bin/activate && cd dialogue/others && rasa run --log-file $log_dir/others_rasa.log -v -p $others_rasa_port --enable-api &"
    ;;

   "all")
    echo "kitchen dialogue service start...."
    su root -c "source venv/bin/activate && cd dialogue/kitchen && rasa run --log-file $log_dir/kitchen_rasa.log -v -p $kitchen_rasa_port --enable-api &"

    echo "patent dialogue service start...."
    su root -c "source venv/bin/activate && cd dialogue/patent && rasa run --log-file $log_dir/patent_rasa.log -v -p $patent_rasa_port --enable-api &"

    echo "others dialogue service start...."
    su root -c "source venv/bin/activate && cd dialogue/others && rasa run --log-file $log_dir/others_rasa.log -v -p $others_rasa_port --enable-api &"

  esac
}

#停止服务方法
stop() {
  echo "Please input the stop server name:kitchen|patent|others|all"
  read name
  case $name in
  "kitchen")
    echo "$name dialogue service stop...."
    echo $kitchen_rasa_port
    PROCESS=`lsof -t -i:$kitchen_rasa_port`
    kill -9 $PROCESS
    echo kill $PROCESS
    ;;

  "patent")
    echo "$name dialogue service stop...."
    echo $patent_rasa_port
    PROCESS=`lsof -t -i:$patent_rasa_port`
    kill -9 $PROCESS
    echo kill $PROCESS
    ;;

  "others")
    echo "$name dialogue service stop...."
    echo $others_rasa_port
    PROCESS=`lsof -t -i:$others_rasa_port`
    kill -9 $PROCESS
    echo kill $PROCESS
    ;;

  "all")
    echo "kitchen dialogue service stop...."
    echo $kitchen_rasa_port
    PROCESS=`lsof -t -i:$kitchen_rasa_port`
    kill -9 $PROCESS
    echo kill $PROCESS

    echo "patent dialogue service stop...."
    echo $patent_rasa_port
    PROCESS=`lsof -t -i:$patent_rasa_port`
    kill -9 $PROCESS
    echo kill $PROCESS

    echo "others dialogue service stop...."
    echo $others_rasa_port
    PROCESS=`lsof -t -i:$others_rasa_port`
    kill -9 $PROCESS
    echo kill $PROCESS
    ;;
  esac
}
#查看服务状态
status() {
  if [ -e $lock ]; then
    echo "$0 service start"
  else
    echo "$0 service stop"
  fi
}
#重新启动
restart() {
  echo "Please input the restart server name:kitchen|patent|others|all"
  read name
  case $name in
  "kitchen")
    echo "$name dialogue service stop...."
    kill -9 $(lsof -i:$kitchen_rasa_port | awk '{print $2}' | tail -n 2)
    echo "$name dialogue service start...."
    su root -c "source venv/bin/activate && cd dialogue/kitchen && rasa run --log-file $log_dir/kitchen_rasa.log -v -p $kitchen_rasa_port --enable-api &"
    ;;

  "patent")
    echo "$name dialogue service stop...."
    kill -9 $(lsof -i:$patent_rasa_port | awk '{print $2}' | tail -n 2)
    echo "$name dialogue service start...."
    su root -c "source venv/bin/activate && cd dialogue/patent && rasa run --log-file $log_dir/patent_rasa.log -v -p $patent_rasa_port --enable-api &"
    ;;

  "others")
    echo "$name dialogue service stop...."
    kill -9 $(lsof -i:$others_rasa_port | awk '{print $2}' | tail -n 2)
    echo "$name dialogue service start...."
    su root -c "source venv/bin/activate && cd dialogue/others && rasa run --log-file $log_dir/others_rasa.log -v -p $others_rasa_port --enable-api &"
    ;;
  "all")
    echo "kitchen dialogue service stop...."
    kill -9 $(lsof -i:$kitchen_rasa_port | awk '{print $2}' | tail -n 2)
    echo "kitchen dialogue service start...."
    su root -c "source venv/bin/activate && cd dialogue/kitchen && rasa run --log-file $log_dir/kitchen_rasa.log -v -p $kitchen_rasa_port --enable-api &"

    echo "patent dialogue service stop...."
    kill -9 $(lsof -i:$patent_rasa_port | awk '{print $2}' | tail -n 2)
    echo "patent dialogue service start...."
    su root -c "source venv/bin/activate && cd dialogue/patent && rasa run --log-file $log_dir/patent_rasa.log -v -p $patent_rasa_port --enable-api &"

    echo "others dialogue service stop...."
    kill -9 $(lsof -i:$others_rasa_port | awk '{print $2}' | tail -n 2)
    echo "others dialogue service start...."
    su root -c "source venv/bin/activate && cd dialogue/others && rasa run --log-file $log_dir/others_rasa.log -v -p $others_rasa_port --enable-api &"
    ;;
  esac
}

server() {
  echo "Please input the server action name:start|stop|status|restart|skill"
  read name
  case $name in
  "start")
    start
    ;;
  "stop")
    stop
    ;;
  "status")
    status
    ;;
  "restart")
    restart
    ;;
  "skill")
    skill
    ;;
  esac
}

server
