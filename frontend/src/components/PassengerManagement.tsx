import { useState, useEffect } from "react";
import { Card, Table, Button, Space, Modal, Form, Input, message, Popconfirm } from "antd";
import { UserOutlined, DeleteOutlined, EditOutlined, PlusOutlined } from "@ant-design/icons";
import { PSS_API_URL } from "../services/api";

export const PassengerManagement = () => {
  const [passengers, setPassengers] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [isModalVisible, setIsModalVisible] = useState(false);
  const [editingPassenger, setEditingPassenger] = useState<any>(null);
  const [form] = Form.useForm();

  const fetchPassengers = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${PSS_API_URL}/passengers`);
      if (res.ok) {
        const data = await res.json();
        setPassengers(data);
      } else {
        message.error("Failed to load passengers");
      }
    } catch (e) {
      message.error("API connection error");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPassengers();
  }, []);

  const handleAdd = () => {
    setEditingPassenger(null);
    form.resetFields();
    setIsModalVisible(true);
  };

  const handleEdit = (record: any) => {
    setEditingPassenger(record);
    form.setFieldsValue({
      first_name: record.first_name,
      last_name: record.last_name,
      email: record.email,
      phone: record.phone,
      frequent_flyer_number: record.frequent_flyer_number,
    });
    setIsModalVisible(true);
  };

  const handleDelete = async (passengerId: string) => {
    try {
      const res = await fetch(`${PSS_API_URL}/passengers/${passengerId}`, {
        method: "DELETE"
      });
      if (res.ok) {
        message.success("Passenger deleted (and all associated bookings removed).");
        fetchPassengers();
      } else {
        message.error("Failed to delete passenger");
      }
    } catch (e) {
      message.error("API connection error");
    }
  };

  const handleModalOk = async () => {
    try {
      const values = await form.validateFields();
      if (editingPassenger) {
        // Update
        const res = await fetch(`${PSS_API_URL}/passengers/${editingPassenger.passenger_id}`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(values),
        });
        if (res.ok) {
          message.success("Passenger updated");
          setIsModalVisible(false);
          fetchPassengers();
        } else {
          message.error("Failed to update passenger");
        }
      } else {
        // Create
        const res = await fetch(`${PSS_API_URL}/passengers`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(values),
        });
        if (res.ok) {
          message.success("Passenger created");
          setIsModalVisible(false);
          fetchPassengers();
        } else {
          message.error("Failed to create passenger");
        }
      }
    } catch (e) {
      // validation error or network error
    }
  };

  const columns = [
    {
      title: "ID",
      dataIndex: "passenger_id",
      key: "passenger_id",
      render: (id: string, record: any) => <code>{record.legacy_id || id}</code>
    },
    {
      title: "Name",
      key: "name",
      render: (record: any) => `${record.first_name} ${record.last_name}`
    },
    {
      title: "Email",
      dataIndex: "email",
      key: "email",
    },
    {
      title: "FF Number",
      dataIndex: "frequent_flyer_number",
      key: "frequent_flyer_number",
    },
    {
      title: "Actions",
      key: "actions",
      render: (record: any) => (
        <Space size="middle">
          <Button icon={<EditOutlined />} onClick={() => handleEdit(record)} />
          <Popconfirm
            title="Delete the passenger?"
            description="Are you sure? This will permanently delete their account and all associated bookings, tickets, and seat assignments."
            onConfirm={() => handleDelete(record.passenger_id)}
            okText="Yes, delete"
            cancelText="Cancel"
            okButtonProps={{ danger: true }}
          >
            <Button danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      )
    }
  ];

  return (
    <Card 
      title={<><UserOutlined /> Passenger Management</>}
      extra={<Button type="primary" icon={<PlusOutlined />} onClick={handleAdd}>Add Passenger</Button>}
      style={{ borderRadius: "12px", boxShadow: "0 4px 12px rgba(0,0,0,0.05)" }}
    >
      <Table 
        dataSource={passengers} 
        columns={columns} 
        rowKey="passenger_id" 
        loading={loading}
        size="small"
      />

      <Modal
        title={editingPassenger ? "Edit Passenger" : "Add New Passenger"}
        open={isModalVisible}
        onOk={handleModalOk}
        onCancel={() => setIsModalVisible(false)}
        destroyOnClose
      >
        <Form form={form} layout="vertical">
          <Form.Item name="first_name" label="First Name" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="last_name" label="Last Name" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="email" label="Email" rules={[{ required: true, type: 'email' }]}>
            <Input />
          </Form.Item>
          <Form.Item name="phone" label="Phone">
            <Input />
          </Form.Item>
          <Form.Item name="frequent_flyer_number" label="Frequent Flyer Number">
            <Input />
          </Form.Item>
        </Form>
      </Modal>
    </Card>
  );
};
