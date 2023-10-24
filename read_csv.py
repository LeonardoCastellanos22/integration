import csv

def read_csv(path):
    with open(path, 'r') as csvfile:
        reader = csv.reader(csvfile)
        data = [row[0] for row in reader]
    return data[1::]

if __name__ == '__main__':
    data = read_csv('./imeibatch.csv')
    print(data)