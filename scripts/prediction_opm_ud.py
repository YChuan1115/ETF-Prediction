
# -*- coding: utf-8 -*-
import pandas as pd
from pandas.tseries.offsets import *
import numpy as np
from sklearn import preprocessing
from sklearn.model_selection import train_test_split
import time 

import keras
from keras.models import Sequential
from keras.layers.core import Dense, Dropout, Activation
from keras.layers.recurrent import LSTM
from keras.utils import np_utils


#macos matplot config
import matplotlib
matplotlib.use('TkAgg')   
import matplotlib.pyplot as plt  


def read_data(file_name, first_time):
	df_name = 'etf_df.csv'

	if first_time :
		df = pd.read_csv(file_name, skipinitialspace=True,encoding = "ISO-8859-1")
		df.dropna(how='any',inplace=True)

		# #change columns name
		cols = ['id','date','name','open','high','low','close','volume']
		df.columns = cols

		#Turn ['date'] type from string('20180130') to date(2018-01-30)
		df['date'] = pd.to_datetime(df['date'], format='%Y%m%d', errors='ignore')
		
		'''
		#Turn feature type to float32
		for c in cols:
			if c not in ['name','date']:
				df[c] = df[c].apply(lambda x: np.float32(x.replace(',','')) if isinstance(df.iloc[0][c], basestring) else np.float32(x))
		'''
		# add up/down of close value as feature
		df['ud']  = np.sign(df['close'].subtract(pd.concat([pd.Series(0), df['close'][0:-1]],ignore_index=True)))

		#save to csv
		#df.to_csv(df_name)

	else:
		df = pd.read_csv(df_name)
		#Turn ['date'] type from string('2018-01-30') to date(2018-01-30)
		df['date'] = pd.to_datetime(df['date'], format='%Y-%m-%d', errors='ignore')
	return df


def data_helper(df, time_frame, train_interval, test_interval, day_offset):
	# data dimensions: id, open(開盤價)、high(最高價)、low(最低價)、volume(成交量)、close(收盤價), 6 dims
	feature_cols = ['id','open','high','low','volume','ud','close']
	number_features = len(feature_cols)
	# extract id
	id_unique = df['id'].unique()
 	# print('id_unique' + str(id_unique))

	#--------------------------#
	# Training data preprocess #
	#--------------------------#
	train_end = pd.date_range(train_interval[0], train_interval[1], freq='B')
	train_result = []

	for _id in id_unique:
		# 要觀察的天數:time_frame 
		for i in range(len(train_end)):
			_time_frame = time_frame
			while(True):
				#filter data by date time interval (BDay : business day)
				df_partial = df[(df['date']>= train_end[i] - BDay(_time_frame) ) & (df['date']<= train_end[i]) & (df['id']== _id)]
				if len(df_partial) >= time_frame+1:
						train_result.append(df_partial[-(time_frame+1):].as_matrix(columns = feature_cols))
						break
				_time_frame += 1
				


	train_result = np.array(train_result).astype(dtype='float32')
	x_train = train_result[:,:-(day_offset)-1] #Extract every time_frame -(day_offset + last day) as feature
	y_train_close = train_result[:,-1][:,-1] # Extract the last one time_frame close(收盤價) value as label
	y_train_ud = train_result[:,-1][:,-2] # Extract the last one time_frame ud(收盤價漲跌) value as label


	#--------------------------#
	# Testing data preprocess #
	#--------------------------#
	test_end = pd.date_range(test_interval[0], test_interval[1], freq='B')
	test_result = []

	for _id in id_unique:
		# 要觀察的天數:time_frame 
		for i in range(len(test_end)):
			_time_frame = time_frame
			while(True):
				#filter data by date time interval (BDay : business day)
				df_partial = df[(df['date']>= test_end[i] - BDay(_time_frame) ) & (df['date']<= test_end[i]) & (df['id']== _id)]
				if len(df_partial) >= time_frame+1:
					test_result.append(df_partial[-(time_frame+1):].as_matrix(columns = feature_cols))
					break
				_time_frame += 1


	test_result = np.array(test_result).astype(dtype='float32')
	x_test = test_result[:,:-(day_offset)-1] #Extract every time_frame -(day_offset + last day) as feature
	y_test_close = test_result[:,-1][:,-1] # Extract the last one time_frame close(收盤價) value as label
	y_test_ud = test_result[:,-1][:,-2] # Extract the last one time_frame ud(收盤價漲跌) value as label


	# print('id_unique' + str(np.unique(x_train[:,0][:,0])))
	return [x_train, y_train_close, y_train_ud, x_test, y_test_close, y_test_ud]





def normalize(df):
	newdf= df.copy()
	min_max_scaler = preprocessing.MinMaxScaler(feature_range=(-1, 1), copy=True)
	newdf['id'] = min_max_scaler.fit_transform(df.id.values.reshape(-1,1))
	newdf['open'] = min_max_scaler.fit_transform(df.open.values.reshape(-1,1))
	newdf['low'] = min_max_scaler.fit_transform(df.low.values.reshape(-1,1))
	newdf['high'] = min_max_scaler.fit_transform(df.high.values.reshape(-1,1))
	newdf['volume'] = min_max_scaler.fit_transform(df.volume.values.reshape(-1,1))
	newdf['close'] = min_max_scaler.fit_transform(df.close.values.reshape(-1,1))
	newdf['ud'] = min_max_scaler.fit_transform(df.ud.values.reshape(-1,1))
	return newdf


def denormalize(col, df, norm_value):
    original_value = df[col].values.reshape(-1,1)
    norm_value = norm_value.reshape(-1,1)    
    min_max_scaler = preprocessing.MinMaxScaler(feature_range=(-1, 1), copy=True)
    min_max_scaler.fit_transform(original_value)
    denorm_value = min_max_scaler.inverse_transform(norm_value)
    
    return denorm_value


def write_csv(id, pred_ud, pred_close, file_name):
	pred_id = np.rint(id).astype(dtype=int).flatten()
	pred_ud = pred_ud.flatten()
	pred_close = pred_close.flatten()

	data = {'ETFid':pred_id, \
			'Mon_ud':pred_ud[0::5], 'Mon_cprice':pred_close[0::5],\
			'Tue_ud':pred_ud[1::5], 'Tue_cprice':pred_close[1::5],\
			'Wed_ud':pred_ud[2::5], 'Wed_cprice':pred_close[2::5],\
			'Thu_ud':pred_ud[3::5], 'Thu_cprice':pred_close[3::5],\
			'Fri_ud':pred_ud[4::5], 'Fri_cprice':pred_close[4::5]}

	pred_df = pd.DataFrame(data=data, columns=['ETFid','Mon_ud', 'Mon_cprice',\
												'Tue_ud', 'Tue_cprice','Wed_ud',\
												'Wed_cprice','Thu_ud', 'Thu_cprice',\
												'Fri_ud', 'Fri_cprice'])


	#wrtie to csv
	pred_df.to_csv(file_name, index=False)



def build_model_close(input_length, input_dim):
    d = 0.2
    model = Sequential()
    model.add(LSTM(64, input_shape=(input_length, input_dim), return_sequences=False))
    model.add(Dropout(d))
    #model.add(LSTM(32, input_shape=(input_length, input_dim), return_sequences=False))
    #model.add(Dropout(d))
    model.add(Dense(18,kernel_initializer="uniform",activation='relu'))
    model.add(Dense(1,kernel_initializer="uniform",activation='linear'))
    model.compile(loss='mse',optimizer='adam', metrics=['accuracy'])
    return model


'''
def build_model_ud(input_length, input_dim):
    d = 0.2
    model = Sequential()
    model.add(LSTM(32, input_shape=(input_length, input_dim), return_sequences=False))
    model.add(Dropout(d))
    model.add(Dense(16,activation='relu'))
    model.add(Dropout(d)) 
    model.add(Dense(3, activation='softmax'))
    model.compile(loss='categorical_crossentropy',optimizer='adam', metrics=['accuracy'])
    return model
'''





def training(x_train, y_train_close, y_train_ud, x_test, y_test_close, y_test_ud,time_frame, day_offset,bset_evaluation,_batch_size,_epochs):
	#------------------------#
	# Close value prediction #
	#------------------------#

	# sequence length(觀察的天數~= time_frame - day_offset) ; feature length (7 dims)
	model_close = build_model_close( time_frame - day_offset, 7 )
	earlyStopping = keras.callbacks.EarlyStopping(monitor='val_loss', patience=7)
	model_close.fit( x_train, y_train_close, batch_size=_batch_size, epochs=_epochs, validation_split=0.1, shuffle=True, verbose=1, callbacks=[earlyStopping])

	# Use trained model to predict
	pred_close = model_close.predict(x_test)
	# denormalize
	denorm_pred_close = denormalize('close', stocks_df, pred_close)
	denorm_ytest_close = denormalize('close', stocks_df, y_test_close)



	'''
	# ------------------------#
	#   ud value prediction   #
	# ------------------------#
	# convert integers to dummy variables (i.e. one hot encoded)
	y_train_ud+= 1 # [drop, balance, up] turn [-1, 0, 1] to [0, 1, 2]
	y_train_categorical_ud = np_utils.to_categorical(y_train_ud)

	# sequence length(觀察的天數~= time_frame - day_offset) ; feature length (7 dims)
	model_ud = build_model_ud( time_frame - day_offset, 7 )
	earlyStopping = keras.callbacks.EarlyStopping(monitor='val_loss', patience=7)
	model_ud.fit( x_train, y_train_categorical_ud, batch_size=16, epochs=1, validation_split=0.1, shuffle=True, verbose=1, callbacks=[earlyStopping])

	# Use trained model to predict
	pred_categorical_ud = model_ud.predict(x_test)
	#inverse value from to_categorical
	pred_ud = np.argmax(pred_categorical_ud, axis= 1)
	pred_ud -= 1 # [drop, balance, up] turn [0, 1, 2] to [-1, 0, 1]
	'''


	# ------------------------#
	#   ud value prediction   #
	# ------------------------#
	# 當天收盤價(使用所預測的股價直)減掉前一天收盤價
	pred_ud = np.diff(denorm_ytest_close, axis = 0)
	pred_ud = np.where(pred_ud >= 0, np.where(pred_ud > 0, 1, 0), -1)

	# 第一天收盤價需要與上禮拜最後一天收盤價比較
	first_close_value = denorm_ytest_close[0,-1]-y_test_close[-1]
	first_close_value = np.where(first_close_value>= 0, np.where(first_close_value > 0, 1, 0), -1)
	pred_ud = np.insert(pred_ud, 0, first_close_value)

	
	#------------------------#
	#      write to csv      #
	#------------------------#
	#儲存較好的submission.csv
	evl = evaluation_function(denorm_pred_close, denorm_ytest_close, pred_ud, y_test_ud)/5
	if evl > bset_evaluation:
		denorm_id = denormalize('id', stocks_df, x_test[:,0][:,0][::5])
		write_csv(denorm_id, pred_ud, denorm_pred_close, 'submission.csv')

	'''
	# ------------------------#
	#         matplot        #
	# ------------------------#
	#matplotlib inline  
	plt.plot(denorm_pred_close,color='red', label='Prediction')
	plt.plot(denorm_ytest_close,color='blue', label='Answer')
	plt.legend(loc='best')
	plt.show()

	#matplotlib inline  
	plt.plot(pred_ud,color='red', label='Prediction')
	plt.plot(y_test_ud,color='blue', label='Answer')
	plt.legend(loc='best')
	plt.show()
	'''
	return evl



# 漲跌: 預測正確得0.5
# 價格: (實際價格 – 絕對值(預測價格 – 實際價格)) /實際價格)*0.5) , 也就預測越正確, 越接近0.5
def evaluation_function(denorm_pred_close, denorm_ytest_close, pred_ud, y_test_ud):

	denorm_pred_close = denorm_pred_close.flatten()
	denorm_ytest_close = denorm_ytest_close.flatten()
	pred_ud = pred_ud.flatten()
	y_test_ud = y_test_ud.flatten()

	# 價格
	value = ((denorm_ytest_close-abs(denorm_pred_close - denorm_ytest_close))/denorm_ytest_close)*0.5

	# 漲跌
	updown = np.array(np.where(pred_ud-y_test_ud==0,0.5,0))

	return np.sum([value.flatten()+updown.flatten()])




if __name__ == "__main__":

	t_start = time.time()
	stocks_df = read_data('TBrain_Round2_DataSet_20180518/tetfp.csv', first_time=True)
	print('[read_data] costs:' + str(time.time() - t_start) + 'secs')
	t_start = time.time()
	stocks_df_normalize = normalize(stocks_df)
	print('[normalize] costs:' + str(time.time() - t_start) + 'secs')
	t_start = time.time()

	# 以time_frame天為一區間進行股價預測(i.e 觀察10天股價, 預測第11天)
	# 觀察1~10天(1 ~ time_feame-day_offset) 預測 5天(day_offset)後 (i.e 第16天) 的股價
	time_frame = 15
	day_offset = 5
	#train_interval = [train_first_day,train_last_day] 
	#(cautions): train_first_day - time_frame >= data first day

	train_interval = ['20180101','20180511']
	test_interval = ['20180514','20180518']
	x_train, y_train_close, y_train_ud, x_test, y_test_close, y_test_ud = data_helper(stocks_df_normalize, time_frame, train_interval, test_interval, day_offset)

	print('[data helper] costs:' + str(time.time() - t_start) + 'secs')
	t_start = time.time()


	batch = [8,10,16,20,32,50,64,100,128]
	epoch = [30,50,75,80,100]


	acc = np.zeros((len(batch),len(epoch)))	
	bset_evaluation = 0

	# 使用不同batch_size與epoch作訓練
	for i in range(0,len(batch)):
		for j in range(0,len(epoch)):
			evl = training(x_train, y_train_close, y_train_ud, x_test, y_test_close, y_test_ud,time_frame, day_offset,bset_evaluation,batch[i],epoch[j])
			acc[i,j] = evl
			if bset_evaluation < evl:	 # 更新最佳bset_evaluation
				bset_evaluation = evl
	print(acc)

	#wrtie to csv
	acc = pd.DataFrame(data=acc)
	acc.to_csv('evaluation.csv', index=False)

